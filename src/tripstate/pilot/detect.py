"""Detectors: anonymous boxes per frame. Oracle/blob run here; model adapters import lazily."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float

    @property
    def long_side(self) -> float:
        return max(self.x2 - self.x1, self.y2 - self.y1)


class Detector(Protocol):
    def detect(self, frame_idx: int, frame: np.ndarray | None) -> list[Detection]: ...


class OracleDetector:
    """Anonymous detections from synthetic truth boxes, with jitter / dropouts / spurious boxes."""

    def __init__(self, truth_boxes: dict[int, dict[int, object]], jitter_px: float = 0.0, dropout: float = 0.0,
                 spurious: float = 0.0, seed: int = 0, loss_windows: dict[int, list[tuple[int, int]]] | None = None):
        self.truth, self.jitter, self.dropout, self.spurious = truth_boxes, jitter_px, dropout, spurious
        self.loss = loss_windows or {}
        self.rng = np.random.default_rng(seed)

    def detect(self, frame_idx: int, frame=None) -> list[Detection]:
        out = []
        for s, b in self.truth.get(frame_idx, {}).items():
            if self.rng.random() < self.dropout or any(a <= frame_idx < bb for a, bb in self.loss.get(s, [])):
                continue
            j = self.rng.normal(0, self.jitter, 4) if self.jitter else np.zeros(4)
            out.append(Detection(b.x1 + j[0], b.y1 + j[1], b.x2 + j[2], b.y2 + j[3], float(0.7 + 0.3 * self.rng.random())))
        if self.spurious and self.rng.random() < self.spurious and out:
            b = out[0]
            out.append(Detection(b.x1 + 300, b.y1 + 50, b.x2 + 300, b.y2 + 50, 0.35))
        order = self.rng.permutation(len(out))
        return [out[i] for i in order]


def _label_components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    """Pure-numpy connected components (8-connectivity via run-length union-find). Returns (x1, y1, x2, y2, area)."""
    h, _w = mask.shape
    parent: list[int] = []

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    runs: list[tuple[int, int, int, int]] = []  # (row, x_start, x_end_exclusive, label)
    prev_runs: list[tuple[int, int, int, int]] = []
    for y in range(h):
        row = mask[y]
        if not row.any():
            prev_runs = []
            continue
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        cur = []
        for s, e in zip(starts, ends):
            lbl = len(parent); parent.append(lbl)
            for (_, ps, pe, pl) in prev_runs:
                if ps < e + 1 and pe > s - 1:   # overlap or diagonal touch
                    union(lbl, pl)
            cur.append((y, int(s), int(e), lbl))
        runs.extend(cur)
        prev_runs = cur
    comps: dict[int, list[int]] = {}
    for y, s, e, lbl in runs:
        r = find(lbl)
        c = comps.setdefault(r, [s, y, e, y + 1, 0])
        c[0], c[1], c[2], c[3] = min(c[0], s), min(c[1], y), max(c[2], e), max(c[3], y + 1)
        c[4] += e - s
    return [tuple(c) for c in comps.values()]


class BlobDetector:
    """Luminance blobs as boxes: a stand-in detector for synthetic video (no model). Filters thin
    structures (rail line) by aspect ratio and small specks by area."""

    def __init__(self, lum_thresh: int = 120, min_area: int = 40, max_aspect: float = 6.0):
        self.lum_thresh, self.min_area, self.max_aspect = lum_thresh, min_area, max_aspect

    def detect(self, frame_idx: int, frame: np.ndarray | None) -> list[Detection]:
        if frame is None:
            return []
        lum = frame.astype(np.int32).sum(axis=2) // 3
        mask = lum > self.lum_thresh
        out = []
        for x1, y1, x2, y2, area in _label_components(mask):
            w, h = x2 - x1, y2 - y1
            if area < self.min_area or max(w, h) / max(1, min(w, h)) > self.max_aspect:
                continue
            fill = area / float(w * h)
            out.append(Detection(float(x1), float(y1), float(x2), float(y2), float(min(1.0, 0.5 + 0.5 * fill))))
        return sorted(out, key=lambda d: (d.x1, d.y1))


class GroundingDinoDetector:
    """Open-vocabulary detector (research 01). Requires `transformers` + `torch`; weights download on first use."""

    def __init__(self, prompts: tuple[str, ...] = ("horse pulling a sulky.", "harness racing horse."),
                 model_id: str = "IDEA-Research/grounding-dino-base", box_thresh: float = 0.3, text_thresh: float = 0.25, device: str = "cpu"):
        try:
            import torch
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install torch transformers  (Grounding DINO adapter)") from e
        self.torch, self.device = torch, device
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device).eval()
        self.text = " ".join(prompts)
        self.box_thresh, self.text_thresh = box_thresh, text_thresh

    def detect(self, frame_idx: int, frame: np.ndarray | None) -> list[Detection]:  # pragma: no cover
        from PIL import Image
        img = Image.fromarray(frame)
        inputs = self.processor(images=img, text=self.text, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            out = self.model(**inputs)
        res = self.processor.post_process_grounded_object_detection(out, inputs.input_ids, box_threshold=self.box_thresh,
                                                                    text_threshold=self.text_thresh, target_sizes=[img.size[::-1]])[0]
        return [Detection(*map(float, b), float(s)) for b, s in zip(res["boxes"].tolist(), res["scores"].tolist())]


class OWLv2Detector:
    """Apache-2.0 open-vocabulary baseline (research 01)."""

    def __init__(self, queries: tuple[str, ...] = ("a horse pulling a sulky", "a trotting horse"),
                 model_id: str = "google/owlv2-base-patch16-ensemble", thresh: float = 0.2, device: str = "cpu"):
        try:
            import torch
            from transformers import Owlv2ForObjectDetection, Owlv2Processor
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install torch transformers  (OWLv2 adapter)") from e
        self.torch, self.device, self.thresh, self.queries = torch, device, thresh, list(queries)
        self.processor = Owlv2Processor.from_pretrained(model_id)
        self.model = Owlv2ForObjectDetection.from_pretrained(model_id).to(device).eval()

    def detect(self, frame_idx: int, frame: np.ndarray | None) -> list[Detection]:  # pragma: no cover
        from PIL import Image
        img = Image.fromarray(frame)
        inputs = self.processor(text=[self.queries], images=img, return_tensors="pt").to(self.device)
        with self.torch.no_grad():
            out = self.model(**inputs)
        res = self.processor.post_process_object_detection(out, threshold=self.thresh, target_sizes=self.torch.tensor([img.size[::-1]]))[0]
        return [Detection(*map(float, b), float(s)) for b, s in zip(res["boxes"].tolist(), res["scores"].tolist())]


class UltralyticsDetector:
    """COCO `horse` class (17) from a YOLO checkpoint; boxes expanded rearward for the sulky (pilot only)."""

    def __init__(self, weights: str = "yolo11n.pt", conf: float = 0.25, expand: float = 1.6, travel_sign: int = 1):
        try:
            from ultralytics import YOLO
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install ultralytics  (AGPL-3.0; YOLO adapter)") from e
        self.model, self.conf, self.expand, self.sign = YOLO(weights), conf, expand, travel_sign

    def detect(self, frame_idx: int, frame: np.ndarray | None) -> list[Detection]:  # pragma: no cover
        r = self.model.predict(frame, classes=[17], conf=self.conf, verbose=False)[0]
        out = []
        for (x1, y1, x2, y2), c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist()):
            w = x2 - x1
            if self.sign > 0:
                x1 = x2 - w * self.expand
            else:
                x2 = x1 + w * self.expand
            out.append(Detection(float(x1), float(y1), float(x2), float(y2), float(c)))
        return out
