"""M1 shot segmenter (SPEC-2.0.0-draft §4 M1; EC-06, EC-07; research 03; RP-15).

Pluggable pieces behind small protocols:
  * CutDetector: per-frame dissimilarity (HistogramCutDetector in numpy; TransNetV2CutDetector lazy);
  * ShotTypeClassifier: shot -> (type, confidence) (BlobShotTypeClassifier for synthetic/pilot; CLIPShotTypeClassifier lazy);
  * StaticOverlayDetector: static bright regions over a shot -> graphic overlay mask (EC-06);
  * replay_insert from slow-motion cadence (duplicate-frame fraction) on wide-pan-looking shots (EC-07).
Shots are contiguous, non-overlapping and cover the whole video; low-confidence types become `other`.
Thresholds live under the `m1_shots` namespace.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import ClassVar, Protocol

import numpy as np

from tripstate.config import ThresholdSet
from tripstate.pilot.detect import BlobDetector

SHOT_TYPES = ("wide_pan", "head_on", "tight", "replay_insert", "graphic_fullscreen", "other")


@dataclass
class ShotRow:
    shot_id: int
    type: str
    t_start_video_s: float
    t_end_video_s: float
    confidence: float
    graphic_overlay_mask_ref: str | None = None
    overlay_fraction: float = 0.0
    dup_fraction: float = 0.0


class CutDetector(Protocol):
    def score(self, prev: np.ndarray | None, frame: np.ndarray) -> float: ...


class HistogramCutDetector:
    """L1 distance between consecutive colour histograms on a downsampled frame, in [0, 1]."""

    def __init__(self, bins: int = 16, step: int = 4):
        self.bins, self.step = bins, step

    def _hist(self, frame: np.ndarray) -> np.ndarray:
        f = frame[:: self.step, :: self.step]
        h = np.concatenate([np.histogram(f[:, :, c], bins=self.bins, range=(0, 256))[0] for c in range(3)]).astype(float)
        return h / max(1.0, h.sum())

    def score(self, prev: np.ndarray | None, frame: np.ndarray) -> float:
        if prev is None:
            return 0.0
        return float(np.abs(self._hist(prev) - self._hist(frame)).sum() / 2.0)


class FrameDiffCutDetector:
    """Mean absolute pixel difference between consecutive downsampled frames, normalised to [0, 1]. `segment`
    applies an adaptive threshold (spike over the running median) so pans do not register as cuts."""

    def __init__(self, step: int = 4):
        self.step = step

    def score(self, prev: np.ndarray | None, frame: np.ndarray) -> float:
        if prev is None:
            return 0.0
        a = prev[:: self.step, :: self.step].astype(np.int16)
        b = frame[:: self.step, :: self.step].astype(np.int16)
        return float(np.abs(a - b).mean() / 255.0)


class TransNetV2CutDetector:
    """Adapter for TransNetV2 (research 03): run `model.predict_frames` on the whole clip, use transition probabilities."""

    def __init__(self, weights_dir: str | None = None):  # pragma: no cover
        try:
            from transnetv2 import TransNetV2
        except ImportError as e:
            raise ImportError("pip install transnetv2 (or vendor the TransNetV2 inference code)") from e
        self.model = TransNetV2(weights_dir) if weights_dir else TransNetV2()
        self.probs: np.ndarray | None = None
        self.i = -1

    def prime(self, frames: list[np.ndarray]) -> None:  # pragma: no cover
        small = np.stack([f[::f.shape[0] // 27 or 1, ::f.shape[1] // 48 or 1][:27, :48] for f in frames])
        self.probs, _ = self.model.predict_frames(small)
        self.i = -1

    def score(self, prev, frame) -> float:  # pragma: no cover
        self.i += 1
        return float(self.probs[self.i]) if self.probs is not None else 0.0


class ShotTypeClassifier(Protocol):
    def classify(self, frames: list[np.ndarray]) -> tuple[str, float]: ...


class BlobShotTypeClassifier:
    """Heuristic for synthetic/pilot footage on bright non-background components (touching runners merge, so
    counts and single-blob sizes are unreliable): a mostly bright frame -> graphic_fullscreen; components spread
    taller than wide -> head_on; a large bright AREA fraction (zoom) -> tight; spread wider than tall -> wide_pan.
    Banner-like components (wider than half the frame) are ignored for typing (EC-06)."""

    def __init__(self, lum_thresh: int = 120, min_area: int = 30, tight_area_frac: float = 0.04):
        self.det = BlobDetector(lum_thresh, min_area)
        self.tight_area_frac = tight_area_frac

    def classify(self, frames: list[np.ndarray]) -> tuple[str, float]:
        votes: dict[str, float] = {}
        for f in frames:
            h, w, _ = f.shape
            lum = f.astype(np.int32).sum(axis=2) // 3
            if float((lum > 150).mean()) > 0.6:
                votes["graphic_fullscreen"] = votes.get("graphic_fullscreen", 0) + 1
                continue
            dets = [d for d in self.det.detect(0, f) if (d.x2 - d.x1) < 0.5 * w]
            if not dets:
                votes["other"] = votes.get("other", 0) + 1
                continue
            area = sum((d.x2 - d.x1) * (d.y2 - d.y1) for d in dets) / float(w * h)
            ext_x = max(d.x2 for d in dets) - min(d.x1 for d in dets)
            ext_y = max(d.y2 for d in dets) - min(d.y1 for d in dets)
            if ext_y > 1.5 * ext_x:
                votes["head_on"] = votes.get("head_on", 0) + 1
            elif area > self.tight_area_frac:
                votes["tight"] = votes.get("tight", 0) + 1
            elif ext_x > 1.5 * ext_y:
                votes["wide_pan"] = votes.get("wide_pan", 0) + 1
            else:
                votes["other"] = votes.get("other", 0) + 1
        if not votes:
            return "other", 0.0
        best = max(votes, key=votes.get)
        return best, votes[best] / sum(votes.values())


class CLIPShotTypeClassifier:
    """Zero-shot CLIP prompt ensemble (research 03). Prompt texts are non-numeric -> part of extractor_version."""

    PROMPTS: ClassVar[dict[str, list[str]]] = {
        "wide_pan": ["a wide television shot of a harness race, many horses with sulkies on a track", "a long shot of trotting horses racing side by side"],
        "head_on": ["horses and sulkies trotting straight toward the camera", "a head-on view of a harness race"],
        "tight": ["a close-up of one trotting horse and driver", "a tight shot of a single racehorse"],
        "graphic_fullscreen": ["a full-screen television results graphic with text", "a broadcast graphic with names and numbers"],
        "other": ["a crowd in a grandstand", "a television presenter in a studio"],
    }

    def __init__(self, model_id: str = "openai/clip-vit-base-patch32", device: str = "cpu"):  # pragma: no cover
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor
        except ImportError as e:
            raise ImportError("pip install torch transformers (CLIP adapter)") from e
        self.torch, self.device = torch, device
        self.model = CLIPModel.from_pretrained(model_id).to(device).eval()
        self.proc = CLIPProcessor.from_pretrained(model_id)
        self.labels = list(self.PROMPTS)
        texts = [p for lab in self.labels for p in self.PROMPTS[lab]]
        with torch.no_grad():
            te = self.model.get_text_features(**self.proc(text=texts, return_tensors="pt", padding=True).to(device))
        te = te / te.norm(dim=-1, keepdim=True)
        self.text_emb = torch.stack([te[i * 2:(i + 1) * 2].mean(0) for i in range(len(self.labels))])

    def classify(self, frames: list[np.ndarray]) -> tuple[str, float]:  # pragma: no cover
        from PIL import Image
        imgs = [Image.fromarray(f) for f in frames]
        with self.torch.no_grad():
            ie = self.model.get_image_features(**self.proc(images=imgs, return_tensors="pt").to(self.device))
        ie = ie / ie.norm(dim=-1, keepdim=True)
        probs = (100.0 * ie @ self.text_emb.T).softmax(dim=-1).mean(0)
        i = int(probs.argmax())
        return self.labels[i], float(probs[i])


class StaticOverlayDetector:
    """Graphic overlays are bright and temporally static while the scene moves (EC-06, research 03)."""

    def __init__(self, std_max: float = 6.0, lum_min: float = 110.0, step: int = 4):
        self.std_max, self.lum_min, self.step = std_max, lum_min, step

    def mask(self, frames: list[np.ndarray]) -> np.ndarray:
        if len(frames) < 3:
            return np.zeros(frames[0].shape[:2], bool)[:: self.step, :: self.step]
        stack = np.stack([f[:: self.step, :: self.step].astype(np.float32).mean(axis=2) for f in frames])
        return (stack.std(axis=0) < self.std_max) & (stack.mean(axis=0) > self.lum_min)


def duplicate_fraction(frames: list[np.ndarray], rel: float = 0.1, floor: float = 0.05) -> float:
    """Fraction of consecutive frame pairs that are (near-)identical relative to the shot's own motion:
    a pair counts as duplicate when its mean difference is below `rel` × the 90th percentile of pair
    differences in the shot (slow-motion cadence, EC-07). A shot without motion (p90 below `floor`, in
    8-bit units) scores 0 — it is static, not slow."""
    if len(frames) < 3:
        return 0.0
    diffs = np.array([float(np.abs(frames[i + 1][::4, ::4].astype(np.int16) - frames[i][::4, ::4].astype(np.int16)).mean()) for i in range(len(frames) - 1)])
    p90 = float(np.percentile(diffs, 90))
    if p90 < floor:
        return 0.0
    return float(np.mean(diffs < rel * p90))


def segment(frames: list[np.ndarray], fps: float, ts: ThresholdSet, cut_detector: CutDetector | None = None,
            classifier: ShotTypeClassifier | None = None, overlay: StaticOverlayDetector | None = None) -> tuple[list[ShotRow], dict[int, np.ndarray]]:
    """Returns (shots, masks by shot_id). Shots cover [0, n/fps) contiguously."""
    cut_detector = cut_detector or FrameDiffCutDetector()
    classifier = classifier or BlobShotTypeClassifier()
    overlay = overlay or StaticOverlayDetector()
    floor = float(ts.get("cut_diff_floor", 0.02))
    ratio = float(ts.get("cut_diff_ratio", 4.0))
    window = max(3, round(float(ts.get("cut_window_s", 1.0)) * fps))
    min_shot = max(1, round(float(ts["min_shot_s"]) * fps))
    conf_min = float(ts.get("type_conf_min", 0.6))
    dup_min = float(ts.get("replay_dup_fraction_min", 0.35))
    hist = HistogramCutDetector()
    hist_thr = float(ts.get("hist_cut_dist", 0.08))
    n = len(frames)
    scores, hscores = [], []
    prev = None
    for f in frames:
        scores.append(cut_detector.score(prev, f))
        hscores.append(hist.score(prev, f))
        prev = f
    cuts = [0]
    for i in range(1, n):
        recent = [s for s in scores[max(cuts[-1] + 1, i - window):i] if s > 1e-6] or [floor]   # window resets at each cut
        thr = max(floor, ratio * float(np.median(recent)))
        if (scores[i] > thr or hscores[i] > hist_thr) and i - cuts[-1] >= min_shot:
            cuts.append(i)
    bounds = [*cuts, n]
    shots: list[ShotRow] = []
    masks: dict[int, np.ndarray] = {}
    for sid, (a, b) in enumerate(pairwise(bounds)):
        seg_frames = frames[a:b]
        sample = seg_frames[:: max(1, len(seg_frames) // 8)][:8]
        typ, conf = classifier.classify(sample)
        if conf < conf_min:
            typ = "other"
        dup = duplicate_fraction(seg_frames)
        if typ == "wide_pan" and dup >= dup_min:
            typ = "replay_insert"
        row = ShotRow(sid, typ, a / fps, b / fps, conf, dup_fraction=dup)
        if typ == "wide_pan":
            m = overlay.mask(seg_frames)
            row.overlay_fraction = float(m.mean())
            if m.any():
                masks[sid] = m
                row.graphic_overlay_mask_ref = f"mask:{sid}"
        shots.append(row)
    # EC-06: a graphic overlay appearing or vanishing is not a cut. Merge consecutive wide pans whose boundary
    # difference lies inside the union of their static-overlay masks.
    merged: list[ShotRow] = []
    merged_masks: dict[int, np.ndarray] = {}
    for row in shots:
        if merged and merged[-1].type == "wide_pan" and row.type == "wide_pan":
            a, b = merged[-1], row
            ia, ib = round(b.t_start_video_s * fps) - 1, round(b.t_start_video_s * fps)
            if 0 <= ia < ib < n:
                fa, fb = frames[ia][::4, ::4].astype(np.int16), frames[ib][::4, ::4].astype(np.int16)
                d = np.abs(fa - fb).mean(axis=2) / 255.0
                m = np.zeros(d.shape, bool)
                for ref in (masks.get(a.shot_id), masks.get(b.shot_id)):
                    if ref is not None and ref.shape == m.shape:
                        m |= ref
                outside = d[~m].mean() if (~m).any() else 0.0
                if outside < floor:
                    a.t_end_video_s = b.t_end_video_s
                    a.overlay_fraction = max(a.overlay_fraction, b.overlay_fraction)
                    if b.graphic_overlay_mask_ref and not a.graphic_overlay_mask_ref:
                        a.graphic_overlay_mask_ref = f"mask:{a.shot_id}"
                        masks[a.shot_id] = masks[b.shot_id]
                    continue
        merged.append(row)
    for i, row in enumerate(merged):
        if row.shot_id in masks:
            merged_masks[i] = masks[row.shot_id]
            row.graphic_overlay_mask_ref = f"mask:{i}"
        row.shot_id = i
    return merged, merged_masks


def boundary_f1(pred_cuts_s: list[float], true_cuts_s: list[float], tol_s: float = 0.5) -> dict:
    pairs = sorted((abs(p - t), i, j) for i, p in enumerate(pred_cuts_s) for j, t in enumerate(true_cuts_s) if abs(p - t) <= tol_s)
    up: set[int] = set(); ut: set[int] = set(); tp = 0
    for _, i, j in pairs:
        if i in up or j in ut:
            continue
        up.add(i); ut.add(j); tp += 1
    p = tp / len(pred_cuts_s) if pred_cuts_s else (1.0 if not true_cuts_s else 0.0)
    r = tp / len(true_cuts_s) if true_cuts_s else 1.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"f1": f1, "precision": p, "recall": r, "tp": tp}


def type_accuracy(pred: list[ShotRow], truth: list[tuple[float, float, str]], step_s: float = 0.04) -> dict:
    """Time-weighted agreement of shot types, plus wide-pan-vs-rest accuracy (M1 acceptance)."""
    def at(shots, t):
        for s in shots:
            if s[0] <= t < s[1]:
                return s[2]
        return None
    pr = [(s.t_start_video_s, s.t_end_video_s, s.type) for s in pred]
    end = max(t[1] for t in truth)
    ts_ = np.arange(0, end, step_s)
    agree = wide_ok = 0
    for t in ts_:
        a, b = at(pr, t), at(truth, t)
        agree += int(a == b)
        wide_ok += int((a == "wide_pan") == (b == "wide_pan"))
    return {"type_accuracy": agree / len(ts_), "wide_pan_accuracy": wide_ok / len(ts_)}
