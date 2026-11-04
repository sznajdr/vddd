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
  6. rank_long, order_ambiguous, tier_cluster (median-linkage), absolute tier via rail reference;
  7. per-runner conf = frame (axis) confidence × box confidence, so coasted or low-score boxes fall into
     the LOW_CONF band (EC-08) without changing the base state.
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
    sw_px: float | None = None
    axis: tuple[float, float] | None = None     # u_long in image coordinates
    axis_method: str = "none"                   # 'motion' | 'pca' | 'none'
    conf: float = 0.0
    runners: list[RunnerGeometry] = field(default_factory=list)


def _axial_mean(vectors: np.ndarray, trim_deg: float) -> tuple[np.ndarray | None, float]:
    """Robust unsigned mean direction of 2-D vectors (axial data), length-weighted: a short displacement
    carries more relative jitter, so its direction counts less. Returns (unit axis, resultant length)."""
    norms = np.linalg.norm(vectors, axis=1)
    v = vectors[norms > 1e-9]
    wts = norms[norms > 1e-9]
    if len(v) == 0:
        return None, 0.0
    ang = np.arctan2(v[:, 1], v[:, 0])

    def mean_axis(a: np.ndarray, w: np.ndarray) -> tuple[float, float]:
        w = w / w.sum()
        c, s = float((w * np.cos(2 * a)).sum()), float((w * np.sin(2 * a)).sum())
        return 0.5 * math.atan2(s, c), float(math.hypot(c, s))

    theta, r = mean_axis(ang, wts)
    # one trim pass: drop vectors whose axial distance to the mean exceeds trim_deg
    d = np.abs(((ang - theta) + np.pi / 2) % np.pi - np.pi / 2)
    keep = d <= math.radians(trim_deg)
    if keep.sum() >= max(2, len(ang) // 2) and keep.sum() < len(ang):
        theta, r = mean_axis(ang[keep], wts[keep])
    return np.array([math.cos(theta), math.sin(theta)]), r


def _canonical(u: np.ndarray) -> np.ndarray:
    if abs(u[0]) < 1e-12:
        return u if u[1] > 0 else -u
    return u if u[0] > 0 else -u


def _line_intersection(p: np.ndarray, d: np.ndarray, q: np.ndarray, e: np.ndarray) -> np.ndarray | None:
    """Intersection of lines p + s·d and q + t·e (2-D); None when parallel."""
    den = d[0] * e[1] - d[1] * e[0]
    if abs(den) < 1e-9:
        return None
    s = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / den
    return p + s * d


def projective_lateral(point: np.ndarray, u_lat: np.ndarray, rail_p: np.ndarray, rail_d: np.ndarray,
                       fence_p: np.ndarray, fence_d: np.ndarray, width_sl: float) -> float | None:
    """Lateral distance from the rail in SL for an image point, from a 1-D projective map along the
    lateral image line through the point: rail (d = 0), fence (d = width_sl) and the horizon (d = ∞, the
    vanishing point of the two track lines, assumed on a horizontal horizon = no camera roll).
    d(t) = K / (t - t_h) - d0 with t the coordinate along u_lat. Returns None if degenerate."""
    v = _line_intersection(rail_p, rail_d, fence_p, fence_d)
    if v is None:
        return None
    r = _line_intersection(point, u_lat, rail_p, rail_d)
    f = _line_intersection(point, u_lat, fence_p, fence_d)
    h = _line_intersection(point, u_lat, v, np.array([1.0, 0.0]))
    if r is None or f is None or h is None:
        return None
    t_r, t_f, t_h = float((r - point) @ u_lat), float((f - point) @ u_lat), float((h - point) @ u_lat)
    if abs(t_r - t_f) < 1e-9 or abs(t_f - t_h) < 1e-9 or abs(t_r - t_h) < 1e-9:
        return None
    d0 = width_sl * (t_f - t_h) / (t_r - t_f)
    k = (t_r - t_h) * d0
    t_p = 0.0  # the point itself
    if abs(t_p - t_h) < 1e-9:
        return None
    return k / (t_p - t_h) - d0


def nearest_on_polyline(point: np.ndarray, poly: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Closest point on a polyline (N, 2) to `point` and the unit direction of that segment."""
    best = None
    for a, b in pairwise(poly):
        ab = b - a
        L2 = float(ab @ ab)
        if L2 < 1e-12:
            continue
        s = float(np.clip(((point - a) @ ab) / L2, 0.0, 1.0))
        q = a + s * ab
        d = float(np.linalg.norm(point - q))
        if best is None or d < best[0]:
            best = (d, q, ab / math.sqrt(L2))
    if best is None:
        return poly[0], np.array([1.0, 0.0])
    return best[1], best[2]


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
        self.min_vec_sl = float(ts.get("axis_min_vector_sl", 0.05))   # ignore displacements shorter than this (jitter)
        self.lateral_scale = str(ts.get("lateral_scale_mode", "sw_ratio"))   # sw_ratio | rail_fence | rail_fence_projective (RP-19)
        self.axis_source = str(ts.get("axis_source", "motion"))               # motion | rail (RP-22: rail-line direction prior)
        self.half_width_sw = float(ts.get("vehicle_half_width_sw", 0.5))     # RP-23 foot-point correction (projective mode)
        self.track_width_sl = float(ts.get("track_width_sl", 5.8))           # rail-to-fence width in SL (track constant)
        self.smooth_s = float(ts.get("axis_smooth_s", 1.0))             # EMA time constant on the doubled-angle axis
        self._axis_state: np.ndarray | None = None                       # smoothed (cos 2θ, sin 2θ)
        self._axis_state_method = "none"
        self._last_t: float | None = None

    def _motion_vectors(self, t: float, cents: dict[int, tuple[float, float]]) -> dict[int, np.ndarray]:
        past = None
        for ht, hc in reversed(self.history):
            if t - ht >= self.window - 1e-9:
                past = hc
                break
        if past is None:
            return {}
        return {s: np.array(cents[s]) - np.array(past[s]) for s in cents if s in past}

    def _axis(self, vecs: dict[int, np.ndarray], pts: np.ndarray, sl: float) -> tuple[np.ndarray | None, str, float]:
        """Per-frame unsigned axis estimate: motion (length-weighted axial mean of displacements longer
        than axis_min_vector_sl·SL) else PCA of centroids; then temporally smoothed (see _smooth)."""
        good = {s: v for s, v in vecs.items() if np.linalg.norm(v) >= self.min_vec_sl * sl}
        if len(good) >= self.min_vec:
            u, r = _axial_mean(np.stack(list(good.values())), self.trim_deg)
            if u is not None and r >= self.min_res:
                return _canonical(u), "motion", float(min(1.0, r))
        if len(pts) >= 3:
            centred = pts - pts.mean(axis=0)
            _, _, vt = np.linalg.svd(centred, full_matrices=False)
            return _canonical(vt[0]), "pca", self.pca_conf
        return None, "none", 0.0

    def _smooth(self, u: np.ndarray, conf: float, t: float, method: str = "motion") -> np.ndarray:
        """Exponential smoothing of the unsigned axis on the doubled-angle circle (sign-free), weighted by
        the per-frame confidence. Lateral coordinates are extremely sensitive to axis error
        (Δw ≈ (SL/SW)·l·sin δ), so a single frame must not set the axis on its own (RP-21)."""
        th = 2.0 * math.atan2(u[1], u[0])
        obs = np.array([math.cos(th), math.sin(th)])
        if (self._axis_state is None or self._last_t is None or self.smooth_s <= 0
                or (self._axis_state_method == "pca" and method == "motion")):
            self._axis_state = obs          # PCA frames never seed the smoother once motion is available
            self._axis_state_method = method
        else:
            dt = max(1e-6, t - self._last_t)
            alpha = min(1.0, conf * dt / self.smooth_s)
            self._axis_state = (1 - alpha) * self._axis_state + alpha * obs
        self._last_t = t
        st = self._axis_state
        half = 0.5 * math.atan2(st[1], st[0])
        return _canonical(np.array([math.cos(half), math.sin(half)]))

    def project(self, t: float, boxes: list[Box], rail_ref_px: tuple[float, float] | None = None,
                rail_ref_conf: float | None = None, all_saddles: list[int] | None = None,
                fence_ref_px: tuple[float, float] | None = None,
                rail_dir_px: tuple[float, float] | None = None,
                fence_dir_px: tuple[float, float] | None = None,
                rail_polyline_px: np.ndarray | None = None,
                fence_polyline_px: np.ndarray | None = None) -> FrameGeometry:
        cents = {b.saddle_no: b.centroid for b in boxes}
        saddles = sorted(cents)
        missing = [s for s in (all_saddles or []) if s not in cents]
        frame = FrameGeometry(t, None, axis=None, axis_method="none", conf=0.0)

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
        if self.axis_source == "rail" and rail_dir_px is not None and np.linalg.norm(rail_dir_px) > 1e-9:
            u = _canonical(np.asarray(rail_dir_px, float) / np.linalg.norm(rail_dir_px))
            method, conf = "rail", float(rail_ref_conf if rail_ref_conf is not None else 1.0)
        else:
            u, method, conf = self._axis(vecs, pts, sl)
        if u is None:
            return degenerate()
        if method != "rail":      # the rail-line direction is a measurement, not a noisy estimate: never lag it
            u = self._smooth(u, conf, t, method)
        else:
            self._axis_state, self._axis_state_method, self._last_t = None, "rail", t
        u_long = u * self.cal.travel_direction_sign
        u_lat = lateral_unit(u_long, self.cal.rail_side)
        if self.lateral_scale == "rail_fence" and rail_ref_px is not None and fence_ref_px is not None:
            # RP-19: lateral pixel scale from two track lines at a known separation (track_width_sl SL),
            # independent of sw_ratio. SW_px = sep_px * (SW_world / width_world) = sep_px * sw_ratio / track_width_sl.
            sep = abs(float((np.array(fence_ref_px) - np.array(rail_ref_px)) @ u_lat))
            if sep > 1e-6:
                sw = sep * self.sw_ratio / self.track_width_sl
        frame.sw_px = sw
        frame.axis, frame.axis_method, frame.conf = (float(u_long[0]), float(u_long[1])), method, conf

        origin = np.median(pts, axis=0)
        rel = pts - origin
        local_axes: dict[int, np.ndarray] = {}
        if self.k_local > 0 and len(vecs) >= self.min_vec:  # local axis per runner (RP-20): longitudinal AND lateral
            for i, s in enumerate(saddles):
                d = np.linalg.norm(pts - pts[i], axis=1)
                near = [saddles[j] for j in np.argsort(d)[: self.k_local + 1] if saddles[j] in vecs]
                ul, _ = _axial_mean(np.stack([vecs[n] for n in near]), self.trim_deg) if len(near) >= 2 else (None, 0.0)
                local_axes[s] = _canonical(ul) * self.cal.travel_direction_sign if ul is not None else u_long
        l = {s: float(rel[i] @ local_axes.get(s, u_long)) / sl for i, s in enumerate(saddles)}
        w = {s: float(rel[i] @ lateral_unit(local_axes.get(s, u_long), self.cal.rail_side)) / sw for i, s in enumerate(saddles)}

        rail_w = rail_conf = None
        if rail_ref_px is not None and rail_ref_conf is not None:
            rail_w = float((np.array(rail_ref_px) - origin) @ u_lat) / sw
            rail_conf = float(rail_ref_conf)
        if (self.lateral_scale == "rail_fence_projective" and rail_ref_px is not None and fence_ref_px is not None
                and rail_dir_px is not None and fence_dir_px is not None and rail_ref_conf is not None):
            # RP-19 (refined): perspective-correct lateral coordinate from the rail and fence lines and their
            # vanishing point; w = distance from the rail in SW, so rail_ref_w = 0 and lane 0 sits at +0.5.
            rp, rd = np.array(rail_ref_px, float), np.array(rail_dir_px, float)
            fp, fd = np.array(fence_ref_px, float), np.array(fence_dir_px, float)
            w_proj: dict[int, float] = {}
            box_by = {b.saddle_no: b for b in boxes}
            for i, s in enumerate(saddles):
                if rail_polyline_px is not None and fence_polyline_px is not None and len(rail_polyline_px) > 1 and len(fence_polyline_px) > 1:
                    # local datum (bends): nearest rail / fence segment to the runner's foot point
                    rp_i, rd_i = nearest_on_polyline(pts[i], np.asarray(rail_polyline_px, float))
                    fp_i, fd_i = nearest_on_polyline(pts[i], np.asarray(fence_polyline_px, float))
                    rd_i = _canonical(rd_i) * self.cal.travel_direction_sign
                else:
                    rp_i, rd_i, fp_i, fd_i = rp, _canonical(rd) * self.cal.travel_direction_sign, fp, fd
                ul_i = lateral_unit(rd_i, self.cal.rail_side)
                # RP-23 foot point: the bbox bottom is the vehicle's NEAR ground edge, which slopes like the rail
                # under pan; move from (mid-x, max-y) up to that edge at mid-x, then from the near edge to the
                # vehicle centre line by half a vehicle width (sign: the near edge has larger image y).
                b = box_by[s]
                slope = abs(rd_i[1] / rd_i[0]) if abs(rd_i[0]) > 1e-9 else 0.0
                foot = np.array([pts[i][0], pts[i][1] - min(slope, 1.0) * (b.x2 - b.x1) / 2.0])
                dd = projective_lateral(foot, ul_i, rp_i, rd_i, fp_i, fd_i, self.track_width_sl)
                if dd is not None:
                    w_near = dd / self.sw_ratio
                    w_proj[s] = w_near - self.half_width_sw * (1.0 if ul_i[1] > 0 else -1.0)
            if len(w_proj) == len(saddles):
                w = w_proj
                rail_w = 0.0
                frame.sw_px = None  # lateral scale is not a single pixel factor in this mode

        order = sorted(saddles, key=lambda s: (-l[s], s))
        rank = {s: i + 1 for i, s in enumerate(order)}
        amb = {s: False for s in saddles}
        for a, b in pairwise(order):
            if l[a] - l[b] < self.tie:
                amb[a] = amb[b] = True
        clusters = cluster_tiers([w[s] for s in saddles], saddles, self.ts)
        tiers = absolute_tiers(clusters, w, rail_w, rail_conf, self.ts)

        box_conf = {b.saddle_no: float(min(1.0, max(0.0, b.conf))) for b in boxes}
        frame.runners = [
            RunnerGeometry(s, l[s], w[s], rank[s], clusters[s], tiers[s], amb[s], rail_w, rail_conf, conf * box_conf[s], True)
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
