"""Synthetic race generator (pack-space truth -> pixel boxes through a panning camera).

Truth is scripted in pack-space (l in SL, w in SW, lane index = tier). Lanes are placed 1.0 SW
apart: an ASSUMPTION consistent with the provisional thresholds, not a measurement (RP-5).
The camera keeps the pack roughly centred with a lag so that residual image motion exists
(the §3.1 motion axis), and a constant on-screen track direction. Box long side = SL_px.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from tripstate.m4_geometry.projection import Box
from tripstate.m5_states.smoothing import FrameGeom


@dataclass
class RunnerScript:
    saddle_no: int
    l_knots: list[tuple[float, float]]        # (race fraction, l_sl)
    w_knots: list[tuple[float, float]]        # (race fraction, w_sw); lane index = round(w)
    visible: list[tuple[float, float]] = field(default_factory=list)  # fractions where NOT visible [a, b)

    def l(self, f: float) -> float:
        xs, ys = zip(*self.l_knots)
        return float(np.interp(f, xs, ys))

    def w(self, f: float) -> float:
        xs, ys = zip(*self.w_knots)
        return float(np.interp(f, xs, ys))

    def is_visible(self, f: float) -> bool:
        return not any(a <= f < b for a, b in self.visible)


@dataclass
class Camera:
    direction_deg: float = 10.0       # on-screen travel direction (image coords, y down)
    sl_px: float = 80.0               # sulky length in pixels (constant zoom)
    sw_ratio: float = 0.35
    pack_speed_sl_per_s: float = 2.5  # pack advance along the track, in SL/s
    lag: float = 0.15                 # fraction of pack displacement the camera fails to follow
    rail_offset_sw: float = -0.5      # rail reference at w = -0.5 SW (lane 0 center at w = 0)
    jitter_px: float = 0.0
    seed: int = 0


@dataclass
class SynthRace:
    runners: list[RunnerScript]
    duration_s: float
    fps: float
    camera: Camera
    t0: float = 0.0

    @property
    def tend(self) -> float:
        return self.t0 + self.duration_s

    def frames(self) -> list[float]:
        n = round(self.duration_s * self.fps)
        return [self.t0 + i / self.fps for i in range(n)]


def truth_frames(race: SynthRace) -> tuple[dict[int, list[FrameGeom]], list[float]]:
    """Ground-truth M4 output straight from the script (tier = lane index + 1)."""
    times = race.frames()
    out: dict[int, list[FrameGeom]] = {}
    for r in race.runners:
        seq = []
        for t in times:
            f = (t - race.t0) / race.duration_s
            if r.is_visible(f):
                seq.append(FrameGeom(t, True, 1.0, r.l(f), r.w(f), round(r.w(f)) + 1))
            else:
                seq.append(FrameGeom(t, False, 0.0))
        out[r.saddle_no] = seq
    return out, times


def render_boxes(race: SynthRace) -> list[tuple[float, list[Box], tuple[float, float]]]:
    """Per frame: (t, boxes, rail reference point in pixels)."""
    cam = race.camera
    rng = np.random.default_rng(cam.seed)
    th = np.radians(cam.direction_deg)
    u_long = np.array([np.cos(th), np.sin(th)])
    # rail on the right of travel in this synthetic camera: visual left = (u_y, -u_x); right = -left
    u_lat_away = np.array([u_long[1], -u_long[0]])          # away from a right-side rail = visual left
    sl, sw = cam.sl_px, cam.sl_px * cam.sw_ratio
    centre = np.array([960.0, 540.0])
    frames = []
    for t in race.frames():
        f = (t - race.t0) / race.duration_s
        advance = cam.pack_speed_sl_per_s * (t - race.t0) * sl          # pack displacement along track (px)
        pan = advance * (1.0 - cam.lag)                                 # camera follows most of it
        boxes = []
        for r in race.runners:
            if not r.is_visible(f):
                continue
            p = centre + u_long * (r.l(f) * sl + advance - pan) + u_lat_away * (r.w(f) * sw)
            if cam.jitter_px:
                p = p + rng.normal(0, cam.jitter_px, 2)
            x, y = float(p[0]), float(p[1])
            boxes.append(Box(r.saddle_no, x - sl / 2, y - sl * 0.6, x + sl / 2, y, 0.95))
        rail = centre + u_long * (advance - pan) + u_lat_away * (cam.rail_offset_sw * sw)
        frames.append((t, boxes, (float(rail[0]), float(rail[1]))))
    return frames


def scripted_race(fps: float = 25.0, duration_s: float = 20.0) -> SynthRace:
    """A small race with a leader, a pocket horse, a parked horse that gets covered, a three-wide
    runner, a 0.6 s occlusion and a late rear detachment."""
    R = RunnerScript
    runners = [
        R(1, [(0, 0.0), (1, 0.0)], [(0, 0.0), (1, 0.0)]),                                  # LEADER on the rail
        R(2, [(0, -1.0), (1, -1.0)], [(0, 0.0), (1, 0.0)]),                                # POCKET
        R(3, [(0, -2.2), (1, -2.2)], [(0, 0.0), (1, 0.0)]),                                # RAIL_COVERED
        R(4, [(0, -0.5), (0.5, -0.5), (0.6, -1.6), (1, -1.6)], [(0, 1.0), (1, 1.0)]),      # PARKED -> drops behind 5 -> OUTSIDE_COVERED
        R(5, [(0, -3.0), (0.5, -3.0), (0.6, -0.4), (1, -0.4)], [(0, 1.0), (1, 1.0)], visible=[(0.2, 0.23)]),  # outside, moves up: becomes PARKED lead
        R(6, [(0, -1.2), (1, -1.2)], [(0, 2.0), (1, 2.0)]),                                # WIDE (tier 3), uncovered
        R(7, [(0, -4.0), (0.7, -4.0), (1, -12.0)], [(0, 0.0), (1, 0.0)]),                  # tail, detaches late
    ]
    return SynthRace(runners, duration_s, fps, Camera())
