"""Live propagation engines and flag monitor for the seeding loop (M3 tool DoD; RP-12; DR-12).

The session drives an engine one frame at a time as the playhead advances; the monitor turns the
engine's per-frame boxes into operator flags exactly once per condition. A re-seed is a new prompt
to the engine from the current frame. Identity still comes only from clicks (D-01): the detector
engine's anonymous tracklets stay anonymous until the operator binds them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tripstate.config import ThresholdSet
from tripstate.pilot.detect import Detection, Detector
from tripstate.pilot.track import IoUTracker, iou
from tripstate.seeding.session import Flag


@dataclass(frozen=True)
class ObjBox:
    box: Detection
    conf: float
    source: str = "propagated"      # propagated | seed | coasted


class LiveEngine(Protocol):
    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> bool: ...
    def step(self, frame: int) -> dict[int, ObjBox]: ...
    def boxes_at(self, frame: int) -> dict[int, ObjBox]: ...
    def anonymous_at(self, frame: int) -> dict[int, Detection]: ...
    def timeline(self) -> dict[int, dict[int, ObjBox]]: ...


class OracleLiveEngine:
    """Streaming oracle on synthetic truth: a prompt inside runner s's box binds obj_id -> s from that frame;
    `loss_windows` {obj: [(a, b)]} drop the box; `conf_dips` {obj: [(a, b, conf)]} lower the mask confidence."""

    def __init__(self, truth_boxes: dict[int, dict[int, object]], loss_windows=None, conf_dips=None):
        self.truth = truth_boxes
        self.loss = loss_windows or {}
        self.dips = conf_dips or {}
        self.binding: dict[int, tuple[int, int]] = {}
        self.cache: dict[int, dict[int, ObjBox]] = {}
        self.last = -1

    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> bool:
        for s, b in self.truth.get(frame, {}).items():
            if b.x1 <= x <= b.x2 and b.y1 <= y <= b.y2:
                self.binding[obj_id] = (s, frame)
                for f in [k for k in self.cache if k >= frame]:
                    self.cache[f].pop(obj_id, None)
                self.last = min(self.last, frame - 1)
                return True
        return False

    def _compute(self, f: int) -> dict[int, ObjBox]:
        out: dict[int, ObjBox] = {}
        for obj, (s, f0) in self.binding.items():
            if f < f0 or s not in self.truth.get(f, {}):
                continue
            if any(a <= f < b for a, b in self.loss.get(obj, [])):
                continue
            conf = next((c for a, b, c in self.dips.get(obj, []) if a <= f < b), 1.0)
            b = self.truth[f][s]
            out[obj] = ObjBox(Detection(b.x1, b.y1, b.x2, b.y2, conf), conf, "seed" if f == f0 else "propagated")
        return out

    def step(self, frame: int) -> dict[int, ObjBox]:
        for f in range(self.last + 1, frame + 1):
            self.cache[f] = self._compute(f)
        self.last = max(self.last, frame)
        return self.cache.get(frame, {})

    def boxes_at(self, frame: int) -> dict[int, ObjBox]:
        return self.cache.get(frame, {})

    def anonymous_at(self, frame: int) -> dict[int, Detection]:
        return {}

    def timeline(self) -> dict[int, dict[int, ObjBox]]:
        return dict(self.cache)


class DetectorLiveEngine:
    """Detector + IoU tracker stepped frame by frame; prompts bind tracklets to saddle numbers (never
    re-association). `frames` is a FrameSource (or None when the detector ignores images)."""

    def __init__(self, detector: Detector, ts: ThresholdSet, fps: float, frames=None):
        self.detector, self.tracker, self.frames = detector, IoUTracker(ts, fps), frames
        self.assignment: dict[int, int] = {}      # track_id -> obj_id
        self.last = -1
        self._imgs = None

    def _img(self, f: int):
        if self.frames is None:
            return None
        if self._imgs is None:
            self._imgs = self.frames.frame_cache()
        return self._imgs[f] if f < len(self._imgs) else None

    def step(self, frame: int) -> dict[int, ObjBox]:
        for f in range(self.last + 1, frame + 1):
            self.tracker.update(f, self.detector.detect(f, self._img(f)))
        self.last = max(self.last, frame)
        return self.boxes_at(frame)

    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> bool:
        self.step(frame)
        hits = [(t.track_id, t.boxes[frame]) for t in self.tracker.tracks.values() if frame in t.boxes
                and t.boxes[frame].x1 <= x <= t.boxes[frame].x2 and t.boxes[frame].y1 <= y <= t.boxes[frame].y2]
        if not hits:
            return False
        hits.sort(key=lambda h: ((h[1].x2 - h[1].x1) * (h[1].y2 - h[1].y1), h[0]))
        tid = hits[0][0]
        for t, o in list(self.assignment.items()):
            if o == obj_id and t != tid and self.tracker.tracks[t].last_frame >= frame:
                del self.assignment[t]          # the correction supersedes the old binding from here on
        self.assignment[tid] = obj_id
        return True

    def boxes_at(self, frame: int) -> dict[int, ObjBox]:
        out: dict[int, ObjBox] = {}
        for tid, obj in self.assignment.items():
            b = self.tracker.tracks[tid].boxes.get(frame)
            if b is not None:
                out[obj] = ObjBox(b, b.conf, "propagated")
        return out

    def anonymous_at(self, frame: int) -> dict[int, Detection]:
        return {tid: t.boxes[frame] for tid, t in self.tracker.tracks.items() if tid not in self.assignment and frame in t.boxes}

    def timeline(self) -> dict[int, dict[int, ObjBox]]:
        out: dict[int, dict[int, ObjBox]] = {}
        for tid, obj in self.assignment.items():
            for f, b in self.tracker.tracks[tid].boxes.items():
                out.setdefault(f, {})[obj] = ObjBox(b, b.conf, "propagated")
        return out


class SAM2LiveEngine:
    """SAM 2 video predictor driven in forward chunks (lookahead frames) so prompts added at the playhead
    take effect immediately; cache invalidated from a new prompt's frame onward. Lazy import, untested here."""

    def __init__(self, video_path: str, checkpoint: str, config: str = "configs/sam2.1/sam2.1_hiera_s.yaml",
                 device: str = "cuda", lookahead: int = 25):
        try:
            import numpy as np
            import torch
            from sam2.build_sam import build_sam2_video_predictor
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install git+https://github.com/facebookresearch/sam2  (SAM 2 live engine)") from e
        self.np, self.torch = np, torch
        self.predictor = build_sam2_video_predictor(config, checkpoint, device=device)
        self.state = self.predictor.init_state(video_path=video_path)
        self.lookahead = lookahead
        self.cache: dict[int, dict[int, ObjBox]] = {}
        self.prompted = False

    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> bool:  # pragma: no cover
        self.predictor.add_new_points_or_box(inference_state=self.state, frame_idx=frame, obj_id=obj_id,
                                             points=self.np.array([[x, y]], dtype=self.np.float32), labels=self.np.array([1], self.np.int32))
        for f in [k for k in self.cache if k >= frame]:
            del self.cache[f]
        self.prompted = True
        return True

    def _propagate(self, start: int, n: int) -> None:  # pragma: no cover
        for frame, obj_ids, logits in self.predictor.propagate_in_video(self.state, start_frame_idx=start, max_frame_num_to_track=n):
            masks = (logits > 0.0).cpu().numpy()
            out: dict[int, ObjBox] = {}
            for k, obj in enumerate(obj_ids):
                ys, xs = self.np.nonzero(masks[k, 0])
                if len(xs) == 0:
                    continue
                conf = float(self.torch.sigmoid(logits[k, 0]).max().item())
                out[int(obj)] = ObjBox(Detection(float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1), conf), conf)
            self.cache[int(frame)] = out

    def step(self, frame: int) -> dict[int, ObjBox]:  # pragma: no cover
        if self.prompted and frame not in self.cache:
            start = max([f for f in self.cache if f < frame], default=frame - 1) + 1
            self._propagate(start, frame - start + 1 + self.lookahead)
        return self.cache.get(frame, {})

    def boxes_at(self, frame: int) -> dict[int, ObjBox]:  # pragma: no cover
        return self.cache.get(frame, {})

    def anonymous_at(self, frame: int) -> dict[int, Detection]:  # pragma: no cover
        return {}

    def timeline(self) -> dict[int, dict[int, ObjBox]]:  # pragma: no cover
        return dict(self.cache)


class FlagMonitor:
    """Stateful flag generation from live boxes: `lost` (no box for lost_flag_s after the prompt),
    `low_conf` (mask conf below mask_conf_flag, at most once per 25 frames per runner), `overlap`
    (two identified boxes with IoU above mask_overlap_flag for overlap_flag_s), `reseed_needed`
    (an anonymous tracklet with enough hits — detector engine only)."""

    def __init__(self, ts: ThresholdSet, fps: float):
        self.conf_thr = float(ts["mask_conf_flag"])
        self.ov_thr = float(ts["mask_overlap_flag"])
        self.ov_frames = max(1, round(float(ts["overlap_flag_s"]) * fps))
        self.lost_frames = max(1, round(float(ts.get("lost_flag_s", 0.2)) * fps))
        self.reseed_min_hits = max(3, round(0.2 * fps))
        self.prompted: dict[int, int] = {}
        self.lost_since: dict[int, int | None] = {}
        self.lost_flagged: dict[int, int | None] = {}
        self.low_last: dict[int, int] = {}
        self.ov_run: dict[tuple[int, int], int] = {}
        self.anon_flagged: set[int] = set()

    def note_prompt(self, frame: int, obj_id: int) -> None:
        self.prompted[obj_id] = frame
        self.lost_since[obj_id] = None
        self.lost_flagged[obj_id] = None

    def update(self, frame: int, boxes: dict[int, ObjBox], anonymous: dict[int, Detection] | None = None) -> list[Flag]:
        flags: list[Flag] = []
        for obj, f0 in self.prompted.items():
            if frame < f0:
                continue
            if obj not in boxes:
                if self.lost_since.get(obj) is None:
                    self.lost_since[obj] = frame
                since = self.lost_since[obj]
                if frame - since + 1 >= self.lost_frames and self.lost_flagged.get(obj) != since:
                    self.lost_flagged[obj] = since
                    flags.append(Flag(frame, "lost", obj, f"no box since frame {since}"))
            else:
                self.lost_since[obj] = None
                ob = boxes[obj]
                if ob.conf < self.conf_thr and frame - self.low_last.get(obj, -10**9) >= 25:
                    self.low_last[obj] = frame
                    flags.append(Flag(frame, "low_conf", obj, f"conf {ob.conf:.2f}"))
        ids = sorted(boxes)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                k = (a, b)
                if iou(boxes[a].box, boxes[b].box) > self.ov_thr:
                    self.ov_run[k] = self.ov_run.get(k, 0) + 1
                    if self.ov_run[k] == self.ov_frames:
                        flags.append(Flag(frame, "overlap", a, f"boxes {a}/{b} overlap for {self.ov_frames} frames"))
                else:
                    self.ov_run[k] = 0
        for tid in (anonymous or {}):
            if tid not in self.anon_flagged:
                self.anon_flagged.add(tid)
                flags.append(Flag(frame, "reseed_needed", None, f"anonymous tracklet {tid}"))
        return flags


class SessionTimelinePropagator:
    """Pilot-runner adapter: replays the live engine timeline stored in a seeding session file."""

    def __init__(self, session: dict):
        self.tl = session.get("timeline") or {}

    def add_prompt(self, frame: int, obj_id: int, x: float, y: float) -> None:
        return None

    def run(self) -> dict[int, dict[int, tuple[Detection, float]]]:
        out: dict[int, dict[int, tuple[Detection, float]]] = {}
        for f, objs in self.tl.items():
            out[int(f)] = {int(o): (Detection(*v[:4], v[4]), float(v[4])) for o, v in objs.items()}
        return out
