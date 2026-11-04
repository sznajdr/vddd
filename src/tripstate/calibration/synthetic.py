"""Synthetic dev/held-out races for the calibration dry run. NOT evidence (§7).

Three static pack-space races (two dev, one held-out) whose runner offsets sit half a grid step away from the grid
points of `cover_lat_sw` (lateral separations 0.55 / 0.75 / 0.85 SW inside the cover window) and `same_tier_sw`
(runners 0.55 and 0.65 SW off a rail cluster whose median stays at 0), so that only the true thresholds (0.8 / 0.6)
reproduce the hand charts: a candidate one grid step away flips a runner into or out of the uncovered-outside mask,
the covered mask or a rest state. Hand charts = the §2 rules at the TRUE threshold set on the exact geometry; the
stored sidecars carry the exact geometry plus small deterministic noise (σ configurable, margins ≥ 0.05)."""
from __future__ import annotations

import numpy as np

from tripstate.calibration.search import DevRace
from tripstate.calibration.sidecar import FrameRecord, RaceGeometry, RunnerRecord, rederive
from tripstate.config import ThresholdSet
from tripstate.m5_states.smoothing import chart_race

RAIL_W = -0.5     # rail reference: lane 0 centre sits at w = 0 = rail_ref + rail_lane_center_offset_sw
SL_PX, BOX_H_PX = 80.0, 48.0

# (saddle, l_sl, w_sw) — see module docstring for why each offset is where it is
# A: 2 sits 0.55 off the rail, uncovered (RAIL_UNCOVERED; PARKED if same_tier_sw <= 0.5); 3 is covered by 2 at 0.75 SW
#    (OUTSIDE_COVERED; PARKED if cover_lat_sw <= 0.7); 4 is the lead PARKED runner; 5 RAIL_COVERED by 2; 6 WIDE uncovered.
RACE_A = [(1, 0.0, 0.0), (2, -2.5, 0.55), (3, -3.3, 1.3), (4, -1.2, 1.5), (5, -4.2, 0.0), (6, -6.0, 2.3)]
# B: 3 sits 0.65 off the rail, uncovered (PARKED; RAIL_UNCOVERED if same_tier_sw >= 0.7); 5 is 0.85 SW outside 4
#    (WIDE uncovered; covered if cover_lat_sw >= 0.9); 6 RAIL_COVERED by 3 at 0.65 (uncovered if cover_lat_sw <= 0.6).
RACE_B = [(1, 0.0, 0.0), (2, -1.0, 0.0), (3, -3.6, 0.65), (4, -1.5, 1.5), (5, -2.3, 2.35), (6, -5.0, 0.0)]
# C (held-out): the A and B mechanisms again in one field, so a wrong threshold set collapses the held-out headline.
RACE_C = [(1, 0.0, 0.0), (2, -2.4, 0.55), (3, -3.2, 1.3), (4, -1.0, 2.1), (5, -1.8, 2.95), (7, -4.0, 0.0)]


def static_geometry(race_id: str, layout: list[tuple[int, float, float]], duration_s: float = 6.0, fps: float = 25.0,
                    noise_sd: float = 0.0, seed: int = 0, producer: str = "synthetic") -> RaceGeometry:
    rng = np.random.default_rng(seed)
    saddles = [s for s, _, _ in layout]
    n = round(duration_s * fps)
    frames = []
    for i in range(n):
        t = i / fps
        runners = {}
        for s, l, w in layout:
            dl, dw = (rng.normal(0, noise_sd, 2) if noise_sd > 0 else (0.0, 0.0))
            runners[s] = RunnerRecord(True, 0.95, float(l + dl), float(w + dw), BOX_H_PX)
        frames.append(FrameRecord(t, RAIL_W, 0.9, SL_PX, runners))
    return RaceGeometry(race_id, 0.0, duration_s, [(0.0, duration_s)], saddles, frames, producer)


def hand_chart_from(geom: RaceGeometry, true_ts: ThresholdSet, split: str) -> list[dict]:
    """What a perfect charter writes: the §2 rules at the true thresholds on the exact geometry."""
    frames, times, _ = rederive(geom, true_ts)
    rows = chart_race(frames, times, geom.intervals, geom.t0_video_s, geom.tend_video_s, true_ts)
    return [dict(r, race_id=geom.race_id, method="human_chart", confidence=None, charter_minutes=None, split=split) for r in rows]


def synthetic_races(true_ts: ThresholdSet, noise_sd: float = 0.005, seed: int = 0) -> tuple[list[DevRace], list[DevRace]]:
    """(dev, heldout). Hand charts from exact geometry; stored sidecars noisy."""
    dev, held = [], []
    for i, (rid, layout, split) in enumerate((("SYN-CAL-A", RACE_A, "dev"), ("SYN-CAL-B", RACE_B, "dev"), ("SYN-CAL-C", RACE_C, "heldout"))):
        exact = static_geometry(rid, layout)
        chart = hand_chart_from(exact, true_ts, split)
        noisy = static_geometry(rid, layout, noise_sd=noise_sd, seed=seed + i, producer="synthetic+noise")
        (dev if split == "dev" else held).append(DevRace(rid, noisy, chart, split))
    return dev, held


SYNTHETIC_SPACE = {"cover_lat_sw": [0.6, 0.7, 0.8, 0.9, 1.0], "same_tier_sw": [0.4, 0.5, 0.6, 0.7, 0.8]}
