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
    detached: str | None = None  # 'front' | 'rear' | None (§2.4 overlay)


def assign_lead(parked_l: dict[int, float], tie: float) -> dict[int, tuple[bool | None, bool]]:
    """lead_uncovered_outside (L-12): the uniquely furthest-advanced PARKED runner; ties within
    rank_tie_sl -> all tied runners (None, True); at most one True per frame."""
    if not parked_l:
        return {}
    order = sorted(parked_l, key=lambda s: (-parked_l[s], s))
    top = order[0]
    tied = [s for s in order[1:] if parked_l[top] - parked_l[s] < tie]
    out: dict[int, tuple[bool | None, bool]] = {}
    if tied:
        for s in [top, *tied]:
            out[s] = (None, True)
        for s in order[1 + len(tied):]:
            out[s] = (False, False)
    else:
        out[top] = (True, False)
        for s in order[1:]:
            out[s] = (False, False)
    return out


def detached_overlay(l_valid: dict[int, float], detach_sl: float) -> dict[int, str]:
    """§2.4 DETACHED: front iff rank 1 is > detach_sl ahead of rank 2; rear iff last is
    > detach_sl behind second-last. Caller suppresses when a boundary neighbour may be off-frame (EC-02)."""
    if len(l_valid) < 2:
        return {}
    order = sorted(l_valid, key=lambda s: (-l_valid[s], s))
    out: dict[int, str] = {}
    if l_valid[order[0]] - l_valid[order[1]] > detach_sl:
        out[order[0]] = "front"
    if l_valid[order[-2]] - l_valid[order[-1]] > detach_sl:
        out[order[-1]] = "rear"
    return out


def classify_frame(
    runners: list[RunnerGeom],
    ts: ThresholdSet,
    covered_override: dict[int, bool] | None = None,
    allow_detached: bool = True,
) -> list[RunnerState]:
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
    if covered_override is not None:  # smoothed predicate (L-11) supplied by M5 smoothing
        cov = {s: covered_override.get(s, cov[s]) for s in cov}

    tier_of = {r.saddle_no: r.tier for r in valid}

    def base_states(order: list[int]) -> dict[int, tuple[str, str]]:
        """(state, reason) per valid runner given an explicit rank ordering (front first)."""
        pos = {s_: i for i, s_ in enumerate(order)}
        tier1 = [s_ for s_ in order if tier_of[s_] == 1]
        res: dict[int, tuple[str, str]] = {}
        for s_ in order:
            c = cov[s_]
            if tier_of[s_] == 1:
                ahead = sum(1 for o in tier1 if pos[o] < pos[s_])
                if ahead == 0:
                    # RP-11: rail leadership takes precedence; cover remains an independent attribute.
                    res[s_] = ("LEADER", "")
                elif c and ahead == 1:
                    res[s_] = ("POCKET", "")
                elif c:
                    res[s_] = ("RAIL_COVERED", "")
                else:
                    res[s_] = ("RAIL_UNCOVERED", "")
            elif tier_of[s_] == 2:
                res[s_] = ("OUTSIDE_COVERED" if c else "PARKED", "")
            else:
                res[s_] = ("WIDE", "")
        return res

    # Rank ordering: descending l_sl, saddle_no as a deterministic storage tiebreak only (§2.2).
    order = [r.saddle_no for r in sorted(valid, key=lambda r: (-l[r.saddle_no], r.saddle_no))]
    base = base_states(order)
    # order_ambiguous: adjacent runners closer than rank_tie_sl (including exact ties). If reversing
    # their order would change a runner's base state, that runner is UNKNOWN: the tiebreak is not
    # geometric evidence.
    ambiguous: set[int] = set()
    for idx in range(len(order) - 1):
        a, b = order[idx], order[idx + 1]
        if l[a] - l[b] < tie:
            swapped = list(order)
            swapped[idx], swapped[idx + 1] = b, a
            alt = base_states(swapped)
            for s_ in (a, b):
                if alt[s_][0] != base[s_][0]:
                    ambiguous.add(s_)

    parked: list[RunnerGeom] = []
    for r in valid:
        s = r.saddle_no
        c = cov[s]
        low = min_conf <= r.conf < ok_conf
        st, reason = base[s]
        if s in ambiguous:
            out[s] = RunnerState(s, "UNKNOWN", c, None, None, None, low, "order_ambiguous")
        elif st == "UNKNOWN":
            out[s] = RunnerState(s, "UNKNOWN", c, None, None, None, low, reason)
        elif st == "PARKED":
            out[s] = RunnerState(s, "PARKED", False, None, None, None, low)
            parked.append(r)
        elif st == "WIDE":
            out[s] = RunnerState(s, "WIDE", c, False, False, r.tier, low)
        else:
            out[s] = RunnerState(s, st, c, False, False, None, low)

    for s_, (lead, amb) in assign_lead({r.saddle_no: l[r.saddle_no] for r in parked}, tie).items():
        out[s_].lead_uncovered_outside = lead
        out[s_].lead_uncovered_outside_ambiguous = amb

    if allow_detached:
        for s_, end in detached_overlay(l, float(ts["detach_sl"])).items():
            out[s_].detached = end

    return [out[r.saddle_no] for r in runners]
