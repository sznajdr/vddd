"""Pack principal axis and projection (SPEC-2.0.0-draft §3.1–3.2; D-07; EC-13; research 05).

Reference implementation on already-detected boxes. Rail detection in pixels is NOT done here:
the caller supplies an optional rail reference point in pixel space per frame (from M1/M4 rail
detection or human calibration) and its confidence.

Per frame:
  1. centroid c_i = (mid-x, max-y) of each horse_sulky box (point nearest the track plane);
  2. SL = median box long side; SW = SL * sw_ratio;
  3. motion vectors over motion_window_s per track; unsigned axis = robust mean of unit vectors
     (axial statistics on doubled angles, one outlier-trim pass); fallback PCA of centroids when
     fewer than axis_min_vectors vectors or resultant < axis_min_resultant;
  4. canonicalize to +x (or +y when x == 0); orient by travel_direction_sign; u_lat sign so that
     increasing w = away from the rail (rail_side per shot);
  5. l = c·u_long / SL, w = c·u_lat / SW (origin = pack median; only differences matter);
  6. rank_long, order_ambiguous, tier_cluster (median-linkage), absolute tier via rail reference.
Degenerate frames (pack < pack_min_visible, unstable axis, missing calibration) -> conf = 0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

import numpy as np

from tripstate.config import ThresholdSet
from tripstate.m4_geometry.tiering import absolute_tiers, cluster_tiers


@dataclass(frozen=True)
class Box:
    saddle_no: int
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float = 1.0

    @property
    def centroid(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, max(self.y1, self.y2))

    @property
    def long_side(self) -> float:
        return max(abs(self.x2 - self.x1), abs(self.y2 - self.y1))


@dataclass(frozen=True)
class ShotCalibration:
    travel_direction_sign: int           # +1 / -1 relative to the canonical (+x) axis
    rail_side: str                       # 'left_of_travel' | 'right_of_travel'
    human_confirmed: bool = False


@dataclass
class RunnerGeometry:
    saddle_no: int
    l_sl: float | None
    w_sw: float | None
    rank_long: int | None
    tier_cluster: int | None
    tier: int | None
    order_ambiguous: bool
    rail_ref_w_sw: float | None
    rail_ref_conf: float | None
    conf: float
    detected: bool = True


@dataclass
class FrameGeometry:
    t: float
    sl_px: float | None
    axis: tuple[float, float] | None     # u_long in image coordinates
    axis_method: str                     # 'motion' | 'pca' | 'none'
    conf: float
    runners: list[RunnerGeometry] = field(default_factory=list)


def _axial_mean(vectors: np.ndarray, trim_deg: float) -> tuple[np.ndarray | None, float]:
    """Robust unsigned mean direction of 2-D vectors (axial data). Returns (unit axis, resultant length)."""
    v = vectors[np.linalg.norm(vectors, axis=1) > 1e-9]
    if len(v) == 0:
        return None, 0.0
    ang = np.arctan2(v[:, 1], v[:, 0])

    def mean_axis(a: np.ndarray) -> tuple[float, float]:
        c, s = np.cos(2 * a).mean(), np.sin(2 * a).mean()
        return 0.5 * math.atan2(s, c), float(math.hypot(c, s))

    theta, r = mean_axis(ang)
    # one trim pass: drop vectors whose axial distance to the mean exceeds trim_deg
    d = np.abs(((ang - theta) + np.pi / 2) % np.pi - np.pi / 2)
    keep = d <= math.radians(trim_deg)
    if keep.sum() >= max(2, len(ang) // 2) and keep.sum() < len(ang):
        theta, r = mean_axis(ang[keep])
    return np.array([math.cos(theta), math.sin(theta)]), r


def _canonical(u: np.ndarray) -> np.ndarray:
    if abs(u[0]) < 1e-12:
        return u if u[1] > 0 else -u
    return u if u[0] > 0 else -u


def lateral_unit(u_long: np.ndarray, rail_side: str) -> np.ndarray:
    """Image coordinates (y down). Visual left of travel = (u_y, -u_x). Increasing w must point away
    from the rail: rail on the left -> u_lat points right; rail on the right -> u_lat points left."""
    left = np.array([u_long[1], -u_long[0]])
    if rail_side == "left_of_travel":
        return -left
    if rail_side == "right_of_travel":
        return left
    raise ValueError(f"rail_side {rail_side!r}")


class ShotProjector:
    """Stateful over one wide-pan shot: keeps the centroid history needed for motion vectors."""

    def __init__(self, ts: ThresholdSet, calibration: ShotCalibration | None, fps: float):
        self.ts = ts
        self.cal = calibration
        self.fps = fps
        self.history: list[tuple[float, dict[int, tuple[float, float]]]] = []
        self.window = float(ts["motion_window_s"])
        self.sw_ratio = float(ts["sw_ratio"])
        self.min_vec = int(ts.get("axis_min_vectors", 3))
        self.min_res = float(ts.get("axis_min_resultant", 0.7))
        self.pca_conf = float(ts.get("axis_pca_conf", 0.6))
        self.trim_deg = float(ts.get("axis_trim_deg", 45.0))
        self.min_visible = int(ts.get("pack_min_visible", 3))
        self.tie = float(ts["rank_tie_sl"])
        self.k_local = int(ts.get("axis_neighbourhood_k", 0))

    def _motion_vectors(self, t: float, cents: dict[int, tuple[float, float]]) -> dict[int, np.ndarray]:
        past = None
        for ht, hc in reversed(self.history):
            if t - ht >= self.window - 1e-9:
                past = hc
                break
        if past is None:
            return {}
        return {s: np.array(cents[s]) - np.array(past[s]) for s in cents if s in past}

    def _axis(self, vecs: dict[int, np.ndarray], pts: np.ndarray) -> tuple[np.ndarray | None, str, float]:
        if len(vecs) >= self.min_vec:
            u, r = _axial_mean(np.stack(list(vecs.values())), self.trim_deg)
            if u is not None and r >= self.min_res:
                return _canonical(u), "motion", float(min(1.0, r))
        if len(pts) >= 3:
            centred = pts - pts.mean(axis=0)
            _, _, vt = np.linalg.svd(centred, full_matrices=False)
            return _canonical(vt[0]), "pca", self.pca_conf
        return None, "none", 0.0

    def project(self, t: float, boxes: list[Box], rail_ref_px: tuple[float, float] | None = None,
                rail_ref_conf: float | None = None, all_saddles: list[int] | None = None) -> FrameGeometry:
        cents = {b.saddle_no: b.centroid for b in boxes}
        saddles = sorted(cents)
        missing = [s for s in (all_saddles or []) if s not in cents]
        frame = FrameGeometry(t, None, None, "none", 0.0)

        def degenerate() -> FrameGeometry:
            frame.runners = [RunnerGeometry(s, None, None, None, None, None, False, None, None, 0.0, True) for s in saddles]
            frame.runners += [RunnerGeometry(s, None, None, None, None, None, False, None, None, 0.0, False) for s in missing]
            self.history.append((t, cents))
            return frame

        if self.cal is None or len(boxes) < self.min_visible:
            return degenerate()
        sl = float(np.median([b.long_side for b in boxes]))
        if sl <= 0:
            return degenerate()
        frame.sl_px = sl
        sw = sl * self.sw_ratio
        pts = np.array([cents[s] for s in saddles], dtype=float)
        vecs = self._motion_vectors(t, cents)
        u, method, conf = self._axis(vecs, pts)
        if u is None:
            return degenerate()
        u_long = u * self.cal.travel_direction_sign
        u_lat = lateral_unit(u_long, self.cal.rail_side)
        frame.axis, frame.axis_method, frame.conf = (float(u_long[0]), float(u_long[1])), method, conf

        origin = np.median(pts, axis=0)
        rel = pts - origin
        if self.k_local > 0 and len(vecs) >= self.min_vec:  # local axis per runner (RP-20), longitudinal only
            l_vals = []
            for i, s in enumerate(saddles):
                d = np.linalg.norm(pts - pts[i], axis=1)
                near = [saddles[j] for j in np.argsort(d)[: self.k_local + 1] if saddles[j] in vecs]
                ul, _ = _axial_mean(np.stack([vecs[n] for n in near]), self.trim_deg) if len(near) >= 2 else (None, 0.0)
                ul = _canonical(ul) * self.cal.travel_direction_sign if ul is not None else u_long
                l_vals.append(float(rel[i] @ ul) / sl)
            l = dict(zip(saddles, l_vals))
        else:
            l = {s: float(rel[i] @ u_long) / sl for i, s in enumerate(saddles)}
        w = {s: float(rel[i] @ u_lat) / sw for i, s in enumerate(saddles)}

        rail_w = rail_conf = None
        if rail_ref_px is not None and rail_ref_conf is not None:
            rail_w = float((np.array(rail_ref_px) - origin) @ u_lat) / sw
            rail_conf = float(rail_ref_conf)

        order = sorted(saddles, key=lambda s: (-l[s], s))
        rank = {s: i + 1 for i, s in enumerate(order)}
        amb = {s: False for s in saddles}
        for a, b in pairwise(order):
            if l[a] - l[b] < self.tie:
                amb[a] = amb[b] = True
        clusters = cluster_tiers([w[s] for s in saddles], saddles, self.ts)
        tiers = absolute_tiers(clusters, w, rail_w, rail_conf, self.ts)

        frame.runners = [
            RunnerGeometry(s, l[s], w[s], rank[s], clusters[s], tiers[s], amb[s], rail_w, rail_conf, conf, True)
            for s in saddles
        ] + [RunnerGeometry(s, None, None, None, None, None, False, rail_w, rail_conf, 0.0, False) for s in missing]
        self.history.append((t, cents))
        self.history = [h for h in self.history if t - h[0] <= 2 * self.window + 1.0]
        return frame


def to_frame_geoms(frames: list[FrameGeometry], saddles: list[int]) -> tuple[dict[int, list], list[float]]:
    """Adapter to M5: {saddle: [FrameGeom]} + times."""
    from tripstate.m5_states.smoothing import FrameGeom
    out: dict[int, list[FrameGeom]] = {s: [] for s in saddles}
    times: list[float] = []
    for f in frames:
        times.append(f.t)
        by = {r.saddle_no: r for r in f.runners}
        for s in saddles:
            r = by.get(s)
            if r is None or not r.detected:
                out[s].append(FrameGeom(f.t, False, 0.0))
            else:
                out[s].append(FrameGeom(f.t, True, r.conf, r.l_sl, r.w_sw, r.tier))
    return out, times
