"""SHOT_GAP events and coverage fractions (SPEC-2.0.0-draft §2.5, §10, M7; EC-01)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Shot:
    type: str
    t_start_video_s: float
    t_end_video_s: float


def _clip(shots: list[Shot], t0: float, tend: float) -> list[Shot]:
    out = []
    for s in sorted(shots, key=lambda x: x.t_start_video_s):
        a, b = max(s.t_start_video_s, t0), min(s.t_end_video_s, tend)
        if b > a:
            out.append(Shot(s.type, a, b))
    return out


def shot_gap_events(shots: list[Shot], t0: float, tend: float, configured: str = "wide_pan") -> list[dict]:
    """One SHOT_GAP per maximal anchored interval outside the configured shot type. Boundary types
    are NULL at an anchor boundary. source_shot_types preserves source order."""
    clipped = _clip(shots, t0, tend)
    events: list[dict] = []
    i = 0
    while i < len(clipped):
        if clipped[i].type == configured:
            i += 1
            continue
        j = i
        while j + 1 < len(clipped) and clipped[j + 1].type != configured and abs(clipped[j + 1].t_start_video_s - clipped[j].t_end_video_s) < 1e-6:
            j += 1
        a, b = clipped[i].t_start_video_s, clipped[j].t_end_video_s
        before = clipped[i - 1].type if i > 0 and abs(a - t0) > 1e-9 else None
        after = clipped[j + 1].type if j + 1 < len(clipped) and abs(b - tend) > 1e-9 else None
        events.append({
            "type": "SHOT_GAP",
            "t_start_frac": (a - t0) / (tend - t0),
            "t_end_frac": min(1.0, (b - t0) / (tend - t0)),
            "source_shot_types": [s.type for s in clipped[i:j + 1]],
            "shot_type_before": before,
            "shot_type_after": after,
        })
        i = j + 1
    return events


def coverage_fractions(coherent: list[tuple[float, float]], t0: float, tend: float) -> tuple[float, float]:
    """coverage_race and coverage_final_third from pack-coherent intervals (video seconds). Durations, not frames."""
    merged: list[tuple[float, float]] = []
    for a, b in sorted((a, b) for a, b in coherent if b > a):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))

    def covered_len(lo: float, hi: float) -> float:
        return sum(max(0.0, min(b, hi) - max(a, lo)) for a, b in merged)
    race = covered_len(t0, tend) / (tend - t0)
    ft0 = t0 + 2.0 * (tend - t0) / 3.0
    final = covered_len(ft0, tend) / (tend - ft0)
    return race, final
