"""M6 break candidates — UNCALIBRATED reference implementation (SPEC-2.0.0-draft §4 M6, §2.5;
L-15, L-16, L-26; research 04).

Signals (both config-exposed under `m6_events`):
  * vertical-oscillation regime change: box height / SL, detrended by a moving median, windowed
    standard deviation, robust z-score against the race-wide baseline (median / MAD);
  * longitudinal-rank velocity anomaly: places lost over a window, robust z-score.
A candidate opens where either z exceeds its threshold, extends while either stays above half of
it, and closes when both drop for recover_window_s before the series ends (else t_end = None:
unobservable end, DR-10). Candidates closer than candidate_merge_s merge. All candidates start
review_status = pending. Nothing here is calibrated; thresholds are placeholders by design (D-18).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from tripstate.config import ThresholdSet


@dataclass
class BreakCandidate:
    t_start_s: float
    t_end_s: float | None
    score: float
    signals: dict = field(default_factory=dict)
    review_status: str = "pending"


def positions_lost(rank_before: int | None, rank_after: int | None,
                   visible_before: frozenset[int], visible_after: frozenset[int]) -> tuple[int | None, int | None]:
    """F-7 strict form (L-15). Returns (positions_lost, basis_n)."""
    if rank_before is None or rank_after is None or visible_before != visible_after:
        return None, None
    return rank_after - rank_before, len(visible_before)


def _windowed(times: np.ndarray, values: np.ndarray, window_s: float, fn) -> np.ndarray:
    out = np.full(len(times), np.nan)
    j = 0
    for i, t in enumerate(times):
        while times[j] < t - window_s:
            j += 1
        seg = values[j:i + 1]
        seg = seg[~np.isnan(seg)]
        if len(seg) >= 3:
            out[i] = fn(seg)
    return out


def _robust_z(x: np.ndarray) -> np.ndarray:
    valid = x[~np.isnan(x)]
    if len(valid) < 5:
        return np.full(len(x), np.nan)
    base = np.median(valid)
    mad = np.median(np.abs(valid - base)) * 1.4826
    scale = max(mad, 0.1 * abs(base), 1e-6)
    return (x - base) / scale


def oscillation_z(times, box_h_px, sl_px, ts: ThresholdSet) -> np.ndarray:
    t = np.asarray(times, float)
    h = np.asarray([np.nan if v is None else v for v in box_h_px], float) / np.asarray(sl_px, float)
    w = float(ts["osc_window_s"])
    trend = _windowed(t, h, 2 * w, np.median)
    resid = h - trend
    std = _windowed(t, resid, w, np.std)
    return _robust_z(std)


def rank_velocity_z(times, rank_long, ts: ThresholdSet) -> np.ndarray:
    t = np.asarray(times, float)
    r = np.asarray([np.nan if v is None else v for v in rank_long], float)
    w = float(ts["rank_vel_window_s"])
    vel = np.full(len(t), np.nan)
    j = 0
    for i in range(len(t)):
        while t[j] < t[i] - w:
            j += 1
        if not np.isnan(r[i]) and not np.isnan(r[j]) and t[i] - t[j] > 0:
            vel[i] = (r[i] - r[j]) / w  # places lost per window (positive = dropping back)
    return _robust_z(vel)


def break_candidates(times, rank_long, box_h_px, sl_px, ts: ThresholdSet) -> list[BreakCandidate]:
    t = np.asarray(times, float)
    zo = oscillation_z(t, box_h_px, sl_px, ts)
    zr = rank_velocity_z(t, rank_long, ts)
    thr_o, thr_r = float(ts["osc_change_z"]), float(ts["rank_vel_z"])
    recover = float(ts["recover_window_s"])
    merge_s = float(ts["candidate_merge_s"])
    hot = (np.nan_to_num(zo, nan=0.0) > thr_o) | (np.nan_to_num(zr, nan=0.0) > thr_r)
    warm = (np.nan_to_num(zo, nan=0.0) > thr_o / 2) | (np.nan_to_num(zr, nan=0.0) > thr_r / 2)
    cands: list[BreakCandidate] = []
    i = 0
    n = len(t)
    while i < n:
        if not hot[i]:
            i += 1
            continue
        a = i
        while a > 0 and warm[a - 1]:
            a -= 1
        b = i
        while b + 1 < n and warm[b + 1]:
            b += 1
        score = float(np.nanmax(np.concatenate([zo[a:b + 1] / thr_o, zr[a:b + 1] / thr_r])))
        end: float | None = float(t[b + 1]) if b + 1 < n else None
        if end is not None and (t[-1] - end) < recover:
            end = None  # the return to trot is not observed for recover_window_s -> unobservable (DR-10)
        cands.append(BreakCandidate(float(t[a]), end, score, {"osc_z_max": float(np.nanmax(zo[a:b + 1])), "rank_z_max": float(np.nanmax(zr[a:b + 1]))}))
        i = b + 1
    merged: list[BreakCandidate] = []
    for c in cands:
        if merged and (c.t_start_s - (merged[-1].t_end_s if merged[-1].t_end_s is not None else merged[-1].t_start_s)) < merge_s:
            m = merged[-1]
            m.t_end_s = c.t_end_s
            m.score = max(m.score, c.score)
            for k, v in c.signals.items():
                m.signals[k] = max(m.signals.get(k, v), v)
        else:
            merged.append(c)
    return merged
