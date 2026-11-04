"""Seed → tracklet identity assignment (the 1.2.0 comparison path) and flagging (both paths).

Identity is only ever assigned from a human seed (D-01): a click at frame f on a tracklet whose
box contains the point binds that tracklet to the saddle number from f onward. Tracklets never
inherit identity by re-association; a new tracklet appearing after an identified one ends raises
a `reseed_needed` flag for the operator.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from tripstate.pilot.detect import Detection
from tripstate.pilot.track import Track


@dataclass(frozen=True)
class SeedPoint:
    frame: int
    saddle_no: int
    x: float
    y: float


def assign_seeds_to_tracks(tracks: dict[int, Track], seeds: list[SeedPoint]) -> tuple[dict[int, int], list[dict]]:
    """Returns ({track_id: saddle_no}, flags). Later seeds override (human_correction)."""
    assignment: dict[int, int] = {}
    flags: list[dict] = []
    for s in sorted(seeds, key=lambda s: (s.frame, s.saddle_no)):
        hits = [(t.track_id, t.boxes[s.frame]) for t in tracks.values() if s.frame in t.boxes
                and t.boxes[s.frame].x1 <= s.x <= t.boxes[s.frame].x2 and t.boxes[s.frame].y1 <= s.y <= t.boxes[s.frame].y2]
        if not hits:
            flags.append({"frame": s.frame, "kind": "seed_missed", "saddle_no": s.saddle_no, "note": "no tracklet under the click"})
            continue
        hits.sort(key=lambda h: ((h[1].x2 - h[1].x1) * (h[1].y2 - h[1].y1), h[0]))   # smallest box wins on overlap
        tid = hits[0][0]
        prev = [t for t, sad in assignment.items() if sad == s.saddle_no and t != tid]
        for t in prev:
            if tracks[t].last_frame >= s.frame:
                flags.append({"frame": s.frame, "kind": "id_conflict", "saddle_no": s.saddle_no, "note": f"track {t} also carried {s.saddle_no}"})
        assignment[tid] = s.saddle_no
    return assignment, flags


def coast_gaps(boxes: dict[int, Detection], max_gap: int, conf_factor: float = 0.5) -> dict[int, Detection]:
    """EC-08 coasting, offline form: internal gaps of <= max_gap frames between supported boxes are filled by
    linear interpolation with reduced confidence (-> LOW_CONF downstream); longer gaps stay empty (-> NOT_VISIBLE)."""
    if not boxes or max_gap <= 0:
        return dict(boxes)
    out = dict(boxes)
    frames = sorted(boxes)
    for a, b in pairwise(frames):
        gap = b - a - 1
        if 0 < gap <= max_gap:
            ba, bb = boxes[a], boxes[b]
            for f in range(a + 1, b):
                w = (f - a) / (b - a)
                out[f] = Detection(ba.x1 + (bb.x1 - ba.x1) * w, ba.y1 + (bb.y1 - ba.y1) * w,
                                   ba.x2 + (bb.x2 - ba.x2) * w, ba.y2 + (bb.y2 - ba.y2) * w,
                                   min(ba.conf, bb.conf) * conf_factor)
    return out


def identity_timeline(tracks: dict[int, Track], assignment: dict[int, int], n_frames: int, max_gap: int = 0) -> dict[int, dict[int, Detection]]:
    """frame -> saddle -> box for identified tracklets only (anonymous tracklets stay anonymous); gaps coasted per EC-08."""
    tl: dict[int, dict[int, Detection]] = {f: {} for f in range(n_frames)}
    for tid, sad in assignment.items():
        for f, b in coast_gaps(tracks[tid].boxes, max_gap).items():
            if f < n_frames:
                tl[f][sad] = b
    return tl


def reseed_flags(tracks: dict[int, Track], assignment: dict[int, int], expected: list[int], n_frames: int, fps: float) -> list[dict]:
    """Flags for the operator: an identified runner's tracklet ended (lost) while the race continues,
    and anonymous tracklets that appear afterwards (reseed_needed)."""
    flags: list[dict] = []
    for tid, sad in assignment.items():
        t = tracks[tid]
        if t.last_frame < n_frames - 1:
            flags.append({"frame": t.last_frame + 1, "kind": "lost", "saddle_no": sad, "note": f"track {tid} ended"})
    for tid, t in sorted(tracks.items()):
        if tid in assignment:
            continue
        first = min(t.boxes)
        if t.hits >= max(3, int(0.2 * fps)):
            flags.append({"frame": first, "kind": "reseed_needed", "saddle_no": None, "note": f"anonymous track {tid} ({t.hits} hits)"})
    return sorted(flags, key=lambda f: (f["frame"], f["kind"]))


def propagation_flags(prop: dict[int, dict[int, tuple[Detection, float]]], seeded: list[int], n_frames: int,
                      mask_conf_flag: float, overlap_flag: float, overlap_frames: int,
                      prompt_frames: dict[int, int] | None = None) -> list[dict]:
    """Seeded path flags: low mask confidence, loss (no box for a seeded id after its prompt), sustained overlap."""
    from tripstate.pilot.track import iou
    flags: list[dict] = []
    first = prompt_frames or {}
    lost_since: dict[int, int | None] = {s: None for s in seeded}
    overlap_run: dict[tuple[int, int], int] = {}
    for f in range(n_frames):
        objs = prop.get(f, {})
        for s in seeded:
            if f < first.get(s, 0):
                continue
            if s not in objs:
                if lost_since[s] is None:
                    lost_since[s] = f
            else:
                if lost_since[s] is not None and f - lost_since[s] >= 3:
                    flags.append({"frame": lost_since[s], "kind": "lost", "saddle_no": s, "note": f"no mask for {f - lost_since[s]} frames"})
                lost_since[s] = None
                if objs[s][1] < mask_conf_flag:
                    flags.append({"frame": f, "kind": "low_conf", "saddle_no": s, "note": f"mask conf {objs[s][1]:.2f}"})
        ids = sorted(objs)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                k = (a, b)
                if iou(objs[a][0], objs[b][0]) > overlap_flag:
                    overlap_run[k] = overlap_run.get(k, 0) + 1
                    if overlap_run[k] == overlap_frames:
                        flags.append({"frame": f - overlap_frames + 1, "kind": "overlap", "saddle_no": a, "note": f"masks {a}/{b} overlap"})
                else:
                    overlap_run[k] = 0
    for s, since in lost_since.items():
        if since is not None and n_frames - since >= 3:
            flags.append({"frame": since, "kind": "lost", "saddle_no": s, "note": "no mask until the end"})
    # de-duplicate consecutive low_conf flags per runner
    out, last = [], {}
    for fl in sorted(flags, key=lambda x: (x["frame"], x["kind"], x["saddle_no"] or 0)):
        key = (fl["kind"], fl["saddle_no"])
        if fl["kind"] == "low_conf" and last.get(key) is not None and fl["frame"] - last[key] < 25:
            continue
        last[key] = fl["frame"]
        out.append(fl)
    return out
