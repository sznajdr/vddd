"""Tracking-by-detection (anonymous tracklets) and seeded propagation (identity-carrying tracks)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from tripstate.config import ThresholdSet
from tripstate.pilot.detect import Detection


def iou(a, b) -> float:
    ix1, iy1, ix2, iy2 = max(a.x1, b.x1), max(a.y1, b.y1), min(a.x2, b.x2), min(a.y2, b.y2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    ua = (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - inter
    return inter / ua if ua > 0 else 0.0


@dataclass
class Track:
    track_id: int
    boxes: dict[int, Detection] = field(default_factory=dict)   # frame -> box (supported frames only)
    last_frame: int = -1
    hits: int = 0
    velocity: tuple[float, float] = (0.0, 0.0)

    def predict(self, frame: int) -> Detection:
        b = self.boxes[self.last_frame]
        dt = frame - self.last_frame
        dx, dy = self.velocity[0] * dt, self.velocity[1] * dt
        return Detection(b.x1 + dx, b.y1 + dy, b.x2 + dx, b.y2 + dy, b.conf)


class IoUTracker:
    """ByteTrack-style two-stage association with constant-velocity prediction and IoU matching.
    Deterministic: candidates sorted by (IoU desc, track_id, det index). Thresholds from `m3_track`."""

    def __init__(self, ts: ThresholdSet, fps: float):
        self.high = float(ts["track_high_thresh"]); self.low = float(ts["track_low_thresh"])
        self.new_thresh = float(ts["new_track_thresh"]); self.match = float(ts["match_thresh"])
        self.buffer = round(float(ts["track_buffer_s"]) * fps)
        self.tracks: dict[int, Track] = {}
        self.next_id = 1

    def _associate(self, frame: int, active: list[Track], dets: list[tuple[int, Detection]]) -> tuple[list[tuple[Track, int]], list[Track], list[int]]:
        pairs = []
        for t in active:
            p = t.predict(frame)
            for i, d in dets:
                v = iou(p, d)
                if v >= 1.0 - self.match:   # match_thresh is a distance (1 - IoU) in ByteTrack configs
                    pairs.append((-v, t.track_id, i, t))
        pairs.sort()
        used_t: set[int] = set(); used_d: set[int] = set(); matched = []
        for _, tid, i, t in pairs:
            if tid in used_t or i in used_d:
                continue
            used_t.add(tid); used_d.add(i); matched.append((t, i))
        return matched, [t for t in active if t.track_id not in used_t], [i for i, _ in dets if i not in used_d]

    def update(self, frame: int, detections: list[Detection]) -> dict[int, Detection]:
        dets = list(enumerate(detections))
        high = [(i, d) for i, d in dets if d.conf >= self.high]
        low = [(i, d) for i, d in dets if self.low <= d.conf < self.high]
        active = sorted((t for t in self.tracks.values() if frame - t.last_frame <= self.buffer), key=lambda t: t.track_id)
        m1, rem_t, rem_high = self._associate(frame, active, high)
        m2, _, _ = self._associate(frame, rem_t, low)
        out: dict[int, Detection] = {}
        for t, i in m1 + m2:
            d = detections[i]
            prev = t.boxes[t.last_frame]; dt = max(1, frame - t.last_frame)
            t.velocity = (((d.x1 + d.x2) - (prev.x1 + prev.x2)) / 2 / dt, ((d.y1 + d.y2) - (prev.y1 + prev.y2)) / 2 / dt)
            t.boxes[frame] = d; t.last_frame = frame; t.hits += 1
            out[t.track_id] = d
        for i in rem_high:
            d = detections[i]
            if d.conf >= self.new_thresh:
                t = Track(self.next_id, {frame: d}, frame, 1); self.tracks[t.track_id] = t; self.next_id += 1
                out[t.track_id] = d
        return out


class SeededPropagator(Protocol):
    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> None: ...
    def run(self) -> dict[int, dict[int, tuple[Detection, float]]]: ...   # frame -> obj_id -> (box, mask_conf)


class OraclePropagator:
    """Simulates click-seeded mask propagation on synthetic truth: a prompt inside runner s's truth box
    at frame f binds obj_id -> s and returns s's boxes from f onward. `loss_windows` {obj_id: [(f_a, f_b)]}
    simulate propagation failure (no box, conf 0) so the flagging logic can be exercised."""

    def __init__(self, truth_boxes: dict[int, dict[int, object]], loss_windows: dict[int, list[tuple[int, int]]] | None = None):
        self.truth = truth_boxes
        self.loss = loss_windows or {}
        self.binding: dict[int, tuple[int, int]] = {}   # obj_id -> (saddle, from_frame)

    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> None:
        for s, b in self.truth.get(frame, {}).items():
            if b.x1 <= x <= b.x2 and b.y1 <= y <= b.y2:
                self.binding[obj_id] = (s, frame)
                return
        self.binding[obj_id] = (-1, frame)   # click on background: nothing to track

    def run(self) -> dict[int, dict[int, tuple[Detection, float]]]:
        out: dict[int, dict[int, tuple[Detection, float]]] = {}
        for f, boxes in self.truth.items():
            for obj, (s, f0) in self.binding.items():
                if s < 0 or f < f0 or s not in boxes:
                    continue
                if any(a <= f < b for a, b in self.loss.get(obj, [])):
                    continue
                b = boxes[s]
                out.setdefault(f, {})[obj] = (Detection(b.x1, b.y1, b.x2, b.y2, 1.0), 1.0)
        return out


class SAM2Propagator:
    """SAM 2 video predictor adapter (research 02; RP-12). Requires the `sam2` package and a checkpoint.
    Prompts: one positive point per runner with obj_id = saddle number; masks -> boxes."""

    def __init__(self, video_path: str, checkpoint: str, config: str = "configs/sam2.1/sam2.1_hiera_s.yaml", device: str = "cuda"):
        try:
            import torch
            from sam2.build_sam import build_sam2_video_predictor
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install git+https://github.com/facebookresearch/sam2  (SAM 2 adapter)") from e
        self.torch = torch
        self.predictor = build_sam2_video_predictor(config, checkpoint, device=device)
        self.state = self.predictor.init_state(video_path=video_path)
        self.prompts: list[tuple[int, int, float, float]] = []

    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> None:  # pragma: no cover
        import numpy as np
        self.prompts.append((frame, obj_id, x, y))
        self.predictor.add_new_points_or_box(inference_state=self.state, frame_idx=frame, obj_id=obj_id,
                                             points=np.array([[x, y]], dtype=np.float32), labels=np.array([1], np.int32))

    def run(self) -> dict[int, dict[int, tuple[Detection, float]]]:  # pragma: no cover
        out: dict[int, dict[int, tuple[Detection, float]]] = {}
        for frame, obj_ids, logits in self.predictor.propagate_in_video(self.state):
            masks = (logits > 0.0).cpu().numpy()
            for k, obj in enumerate(obj_ids):
                m = masks[k, 0]
                ys, xs = np.nonzero(m)
                if len(xs) == 0:
                    continue
                conf = float(self.torch.sigmoid(logits[k, 0]).max().item())
                out.setdefault(frame, {})[int(obj)] = (Detection(float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1), conf), conf)
        return out
