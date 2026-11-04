"""Per-frame base-state classification (SPEC-2.0.0-draft §2.3 with L-12; D-26/D-27).

Precedence (normative): no detection -> NOT_VISIBLE; conf < min_state_conf -> UNKNOWN;
absolute tier unresolved -> UNKNOWN (EC-13); else exactly one geometric state from
(tier, covered, tier-relative order). Overlays (LOW_CONF) after, never replacing the base.
"""
from __future__ import annotations

from dataclasses import dataclass

from tripstate.config import ThresholdSet
from tripstate.m4_geometry.tiering import covered_all

BASE_STATES = (
    "LEADER", "POCKET", "RAIL_COVERED", "RAIL_UNCOVERED", "OUTSIDE_COVERED",
    "PARKED", "WIDE", "NOT_VISIBLE", "UNKNOWN",
)


@dataclass(frozen=True)
class RunnerGeom:
    saddle_no: int
    detected: bool
    conf: float
    l_sl: float | None = None
    w_sw: float | None = None
    tier: int | None = None  # absolute tier; None = unresolved (EC-13)
    order_ambiguous: bool = False


@dataclass
class RunnerState:
    saddle_no: int
    state: str
    covered: bool | None
    lead_uncovered_outside: bool | None
    lead_uncovered_outside_ambiguous: bool | None
    tier_attr: int | None
    low_conf: bool
    reason: str = ""


def classify_frame(runners: list[RunnerGeom], ts: ThresholdSet) -> list[RunnerState]:
    min_conf = float(ts["min_state_conf"])
    ok_conf = float(ts["ok_state_conf"])
    tie = float(ts["rank_tie_sl"])

    out: dict[int, RunnerState] = {}
    valid: list[RunnerGeom] = []
    for r in runners:
        if not r.detected:
            out[r.saddle_no] = RunnerState(r.saddle_no, "NOT_VISIBLE", None, None, None, None, False)
        elif r.conf < min_conf or r.l_sl is None or r.w_sw is None:
            out[r.saddle_no] = RunnerState(r.saddle_no, "UNKNOWN", None, None, None, None, False, "low_conf")
        elif r.tier is None:
            out[r.saddle_no] = RunnerState(r.saddle_no, "UNKNOWN", None, None, None, None, False, "tier_unresolved")
        else:
            valid.append(r)

    # D-26 cover is computed over all valid (projected) runners, tier-independent.
    l = {r.saddle_no: float(r.l_sl) for r in valid}  # type: ignore[arg-type]
    w = {r.saddle_no: float(r.w_sw) for r in valid}  # type: ignore[arg-type]
    cov = covered_all(l, w, ts)

    tier1 = sorted((r for r in valid if r.tier == 1), key=lambda r: (-l[r.saddle_no], r.saddle_no))
    parked: list[RunnerGeom] = []

    for r in valid:
        s = r.saddle_no
        c = cov[s]
        low = min_conf <= r.conf < ok_conf
        if r.tier == 1:
            ahead = sum(1 for o in tier1 if l[o.saddle_no] > l[s])
            if ahead == 0 and not c:
                st = "LEADER"
            elif ahead == 0 and c:
                # Table gap under D-26 (RP-11): tier-1 front runner covered by an outside runner.
                out[s] = RunnerState(s, "UNKNOWN", c, None, None, None, low, "table_gap_tier1_lead_covered")
                continue
            elif c and ahead == 1:
                st = "POCKET"
            elif c:
                st = "RAIL_COVERED"
            else:
                st = "RAIL_UNCOVERED"
            out[s] = RunnerState(s, st, c, False, False, None, low)
        elif r.tier == 2:
            if c:
                out[s] = RunnerState(s, "OUTSIDE_COVERED", True, False, False, None, low)
            else:
                out[s] = RunnerState(s, "PARKED", False, None, None, None, low)
                parked.append(r)
        else:
            out[s] = RunnerState(s, "WIDE", c, False, False, r.tier, low)

    # lead_uncovered_outside (L-12): the uniquely furthest-advanced PARKED runner; ties within
    # rank_tie_sl -> all tied runners NULL + ambiguous = true; at most one true per frame.
    if parked:
        parked.sort(key=lambda r: (-l[r.saddle_no], r.saddle_no))
        top = parked[0]
        tied = [r for r in parked[1:] if l[top.saddle_no] - l[r.saddle_no] < tie]
        if tied:
            for r in [top, *tied]:
                out[r.saddle_no].lead_uncovered_outside = None
                out[r.saddle_no].lead_uncovered_outside_ambiguous = True
            for r in parked[1 + len(tied):]:
                out[r.saddle_no].lead_uncovered_outside = False
                out[r.saddle_no].lead_uncovered_outside_ambiguous = False
        else:
            out[top.saddle_no].lead_uncovered_outside = True
            out[top.saddle_no].lead_uncovered_outside_ambiguous = False
            for r in parked[1:]:
                out[r.saddle_no].lead_uncovered_outside = False
                out[r.saddle_no].lead_uncovered_outside_ambiguous = False

    return [out[r.saddle_no] for r in runners]
