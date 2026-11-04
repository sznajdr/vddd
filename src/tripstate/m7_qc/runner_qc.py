"""Per-runner QC (SPEC-2.0.0-draft §4 M7, §10 per-runner denominators; EC-03; DR-11 realization tag).

Denominators run from t_0 to t_end (race fraction [0, 1]) except for an EC-03 terminal runner, whose denominator
ends at its confirmed terminal fraction. `visible` = a supported detection exists (state != NOT_VISIBLE);
`stateable` additionally requires a known geometric base state. Non-charted shot time (SHOT_GAP) contributes to
neither numerator. If the denominator does not intersect the final third, both final-third fractions are NULL with
terminal_before_final_third = true; they are never coerced to zero.
"""
from __future__ import annotations

from tripstate.evaluation.metrics import Interval, intersect, length

GEOMETRIC = {"LEADER", "POCKET", "RAIL_COVERED", "RAIL_UNCOVERED", "OUTSIDE_COVERED", "PARKED", "WIDE"}
REALIZATION_TAGS = ("field_gt_14", "cinematic_big_race", "none")


def runner_qc_row(race_id: str, saddle_no: int, segments: list[dict], shot_gaps: list[Interval] | None = None,
                  terminal: tuple[str, float] | None = None) -> dict:
    """segments: this runner's base rows (state, t_start_frac, t_end_frac). shot_gaps: non-charted fractions."""
    gaps = shot_gaps or []
    d_end = min(1.0, terminal[1]) if terminal else 1.0
    denom: list[Interval] = [(0.0, d_end)]
    base = [s for s in segments if s.get("state_kind", "base") == "base"]
    visible = intersect([(s["t_start_frac"], s["t_end_frac"]) for s in base if s["state"] != "NOT_VISIBLE"], denom)
    stateable = intersect([(s["t_start_frac"], s["t_end_frac"]) for s in base if s["state"] in GEOMETRIC], denom)
    # non-charted time contributes to neither numerator (segments never cover it, but guard anyway)
    if gaps:
        visible = _subtract_all(visible, gaps)
        stateable = _subtract_all(stateable, gaps)
    denom_len = length(denom)
    ft = intersect(denom, [(2.0 / 3.0, 1.0)])
    ft_len = length(ft)
    row = {
        "race_id": race_id, "saddle_no": saddle_no,
        "pct_time_visible": length(visible) / denom_len if denom_len > 0 else None,
        "pct_time_stateable": length(stateable) / denom_len if denom_len > 0 else None,
        "pct_final_third_visible": (length(intersect(visible, ft)) / ft_len) if ft_len > 1e-12 else None,
        "pct_final_third_stateable": (length(intersect(stateable, ft)) / ft_len) if ft_len > 1e-12 else None,
        "occl_events": sum(1 for s in base if s["state"] == "NOT_VISIBLE" and s["t_start_frac"] < d_end),
        "denom_start_frac": 0.0, "denom_end_frac": d_end,
        "terminal_reason": terminal[0] if terminal else None, "terminal_frac": terminal[1] if terminal else None,
        "terminal_before_final_third": bool(terminal) and ft_len <= 1e-12,
    }
    return row


def _subtract_all(ivs: list[Interval], gaps: list[Interval]) -> list[Interval]:
    out: list[Interval] = []
    for iv in ivs:
        out.extend(_subtract(iv, gaps))
    return out


def _subtract(iv: Interval, gaps: list[Interval]) -> list[Interval]:
    pieces = [iv]
    for g in sorted(gaps):
        nxt = []
        for a, b in pieces:
            if g[1] <= a or g[0] >= b:
                nxt.append((a, b))
            else:
                if g[0] > a:
                    nxt.append((a, g[0]))
                if g[1] < b:
                    nxt.append((g[1], b))
        pieces = nxt
    return [p for p in pieces if p[1] > p[0]]


def realization_tag(field_size: int, cinematic_big_race: bool = False, max_field: int = 14) -> str:
    """DR-11: why a race was excluded from the corpus by construction (quantifies the selection bias)."""
    if field_size > max_field:
        return "field_gt_14"
    if cinematic_big_race:
        return "cinematic_big_race"
    return "none"
