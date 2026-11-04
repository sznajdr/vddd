"""Temporal smoothing and segment emission (SPEC-2.0.0-draft §3.4, §2.6, §9; EC-01; L-11, L-12).

Pipeline per race (offline, deterministic):
  1. tier hysteresis per runner (a tier change must persist tier_hysteresis_s; committed retroactively
     to the start of the persisting run; shorter excursions keep the committed tier);
  2. raw D-26 cover predicate per frame, then min-duration smoothing of the cover series (L-11);
  3. base-state classification per frame with the smoothed cover;
  4. min-duration smoothing of the base-state series: runs < min_state_s between confident geometric
     states merge into the neighbour with the larger confidence sum (tie -> earlier neighbour);
     NOT_VISIBLE / UNKNOWN runs keep their observed boundaries and are never merged across;
  5. lead_uncovered_outside recomputed per frame after smoothing (at most one True per frame);
  6. segment emission: half-open [t_start_frac, t_end_frac), last charted interval may end at 1.0,
     start/end_truncated at charted-interval edges that are not the anchors (EC-01);
     overlays DETACHED / LOW_CONF emitted as separate rows inheriting visibility + the three
     relational fields and split when any inherited value changes.
BREAKING overlays are appended by M6 after review, never here.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from tripstate.config import ThresholdSet
from tripstate.m4_geometry.tiering import covered_all
from tripstate.m5_states.classify import RunnerGeom, RunnerState, assign_lead, classify_frame

GEOMETRIC = {"LEADER", "POCKET", "RAIL_COVERED", "RAIL_UNCOVERED", "OUTSIDE_COVERED", "PARKED", "WIDE"}


@dataclass(frozen=True)
class FrameGeom:
    """One runner in one frame, as M4 emits it (absolute tier before hysteresis)."""
    t: float
    detected: bool
    conf: float
    l_sl: float | None = None
    w_sw: float | None = None
    tier: int | None = None


def apply_tier_hysteresis(tiers: Sequence[int | None], times: Sequence[float], hysteresis_s: float) -> list[int | None]:
    n = len(tiers)
    out: list[int | None] = [None] * n
    committed: int | None = None
    i = 0
    while i < n:
        raw = tiers[i]
        if raw is None:
            out[i] = None
            i += 1
            continue
        if committed is None or raw == committed:
            committed = raw
            out[i] = committed
            i += 1
            continue
        # candidate change: measure the run of identical raw values starting at i
        j = i
        while j + 1 < n and tiers[j + 1] == raw:
            j += 1
        persisted = (times[j] - times[i]) >= hysteresis_s - 1e-9
        if persisted:
            committed = raw
        for k in range(i, j + 1):
            out[k] = committed
        i = j + 1
    return out


def _runs(values: Sequence) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    s = 0
    for i in range(1, len(values) + 1):
        if i == len(values) or values[i] != values[s]:
            runs.append((s, i - 1))
            s = i
    return runs


def smooth_runs(
    values: list,
    times: Sequence[float],
    confs: Sequence[float],
    min_s: float,
    mergeable: Callable[[object], bool],
    dt_last: float,
) -> list[int]:
    """Return, per frame, the index of the frame whose attributes it should copy after merging.
    Unchanged frames map to themselves. Deterministic, iterated to a fixed point."""
    n = len(values)
    src = list(range(n))
    vals = list(values)
    changed = True
    while changed:
        changed = False
        runs = _runs(vals)
        for ri, (a, b) in enumerate(runs):
            if not mergeable(vals[a]):
                continue
            dur = (times[b + 1] - times[a]) if b + 1 < n else (times[b] - times[a] + dt_last)
            if dur >= min_s - 1e-9:
                continue
            left = runs[ri - 1] if ri > 0 and mergeable(vals[runs[ri - 1][0]]) else None
            right = runs[ri + 1] if ri + 1 < len(runs) and mergeable(vals[runs[ri + 1][0]]) else None
            if left is None and right is None:
                continue
            if left is not None and right is not None:
                cl = sum(confs[left[0]:left[1] + 1])
                cr = sum(confs[right[0]:right[1] + 1])
                target = left if cl >= cr else right
            else:
                target = left if left is not None else right
            donor = target[1] if target is left else target[0]
            for k in range(a, b + 1):
                vals[k] = vals[donor]
                src[k] = src[donor]
            changed = True
            break  # recompute runs after each merge
    return src


def _frac(t: float, t0: float, tend: float) -> float:
    return (t - t0) / (tend - t0)


def chart_race(
    frames: dict[int, list[FrameGeom]],
    times: Sequence[float],
    intervals: Sequence[tuple[float, float]],
    t0: float,
    tend: float,
    ts: ThresholdSet,
    allow_detached: bool = True,
) -> list[dict]:
    """frames: {saddle_no: [FrameGeom per frame]} aligned with `times` (video seconds, increasing);
    intervals: charted wide-pan intervals [s, e) in video seconds inside [t0, tend].
    Returns state_segments-shaped rows (without seg_id/version columns)."""
    saddles = sorted(frames)
    n = len(times)
    if any(len(frames[s]) != n for s in saddles):
        raise ValueError("all runners must have one FrameGeom per frame")
    dt_last = (times[-1] - times[-2]) if n > 1 else 1.0 / 25
    min_s = float(ts["min_state_s"])
    hyst = float(ts["tier_hysteresis_s"])
    min_conf = float(ts["min_state_conf"])
    tie = float(ts["rank_tie_sl"])

    # 1. tier hysteresis
    tiers = {s: apply_tier_hysteresis([f.tier for f in frames[s]], times, hyst) for s in saddles}

    def geom(s: int, i: int) -> RunnerGeom:
        f = frames[s][i]
        return RunnerGeom(s, f.detected, f.conf, f.l_sl, f.w_sw, tiers[s][i])

    def valid(s: int, i: int) -> bool:
        f = frames[s][i]
        return f.detected and f.conf >= min_conf and f.l_sl is not None and f.w_sw is not None

    # 2. raw cover + smoothing of the predicate
    cov_raw: dict[int, list[bool | None]] = {s: [None] * n for s in saddles}
    for i in range(n):
        l = {s: frames[s][i].l_sl for s in saddles if valid(s, i)}
        w = {s: frames[s][i].w_sw for s in saddles if valid(s, i)}
        for s, c in covered_all(l, w, ts).items():  # type: ignore[arg-type]
            cov_raw[s][i] = c
    cov: dict[int, list[bool | None]] = {}
    for s in saddles:
        confs = [frames[s][i].conf for i in range(n)]
        src = smooth_runs(cov_raw[s], times, confs, min_s, lambda v: v is not None, dt_last)
        cov[s] = [cov_raw[s][src[i]] for i in range(n)]

    # 3. classification with smoothed cover
    states: dict[int, list[RunnerState]] = {s: [] for s in saddles}
    for i in range(n):
        override = {s: cov[s][i] for s in saddles if cov[s][i] is not None}
        for st in classify_frame([geom(s, i) for s in saddles], ts, override, allow_detached):
            states[st.saddle_no].append(st)

    # 4. min-duration smoothing of base states
    for s in saddles:
        confs = [frames[s][i].conf for i in range(n)]
        src = smooth_runs([st.state for st in states[s]], times, confs, min_s, lambda v: v in GEOMETRIC, dt_last)
        new = []
        for i in range(n):
            d = states[s][src[i]]
            own = states[s][i]
            new.append(RunnerState(s, d.state, d.covered, None, None, d.tier_attr, own.low_conf, d.reason, own.detached))
        states[s] = new

    # 5. lead recompute per frame
    for i in range(n):
        parked = {s: frames[s][i].l_sl for s in saddles if states[s][i].state == "PARKED" and frames[s][i].l_sl is not None}
        lead = assign_lead(parked, tie)  # type: ignore[arg-type]
        for s in saddles:
            st = states[s][i]
            if st.state in GEOMETRIC:
                st.lead_uncovered_outside, st.lead_uncovered_outside_ambiguous = lead.get(s, (False, False))
            else:
                st.lead_uncovered_outside = st.lead_uncovered_outside_ambiguous = None

    # 6. segment emission
    rows: list[dict] = []
    for s in saddles:
        rows.extend(_emit_runner(s, states[s], frames[s], times, sorted(intervals), t0, tend))
    rows.sort(key=lambda r: (r["saddle_no"], r["state_kind"] != "base", r["t_start_frac"], r["state"]))
    return rows


def _emit_runner(
    s: int,
    st: list[RunnerState],
    fr: list[FrameGeom],
    times: Sequence[float],
    ivs: list[tuple[float, float]],
    t0: float,
    tend: float,
) -> list[dict]:
    n = len(times)

    def interval_of(i: int) -> int | None:
        if i < 0 or i >= n:
            return None
        for k, (a, b) in enumerate(ivs):
            if a <= times[i] < b:
                return k
        return None

    iv_idx = [interval_of(i) for i in range(n)]

    def base_key(i: int) -> tuple:
        x = st[i]
        return (x.state, x.covered, x.lead_uncovered_outside, x.lead_uncovered_outside_ambiguous, x.tier_attr)

    def overlay_keys(i: int) -> set[tuple]:
        x = st[i]
        keys: set[tuple] = set()
        if x.detached:
            keys.add(("DETACHED", x.detached, x.covered, x.lead_uncovered_outside, x.lead_uncovered_outside_ambiguous))
        if x.low_conf and x.state in GEOMETRIC:
            keys.add(("LOW_CONF", None, x.covered, x.lead_uncovered_outside, x.lead_uncovered_outside_ambiguous))
        return keys

    rows: list[dict] = []

    def emit(kind: str, key: tuple, a: int, b: int) -> None:
        k = iv_idx[a]
        iv_a, iv_b = ivs[k]  # type: ignore[index]
        first_in_iv = iv_idx[a - 1] != k if a > 0 else True
        last_in_iv = iv_idx[b + 1] != k if b + 1 < n else True
        t_start = iv_a if first_in_iv else times[a]
        t_end = iv_b if last_in_iv else times[b + 1]
        fs, fe = _frac(t_start, t0, tend), min(1.0, _frac(t_end, t0, tend))
        if fs < 0 or fs > 1 or fe <= fs:
            return
        x = st[a]
        vis = "not_visible" if x.state == "NOT_VISIBLE" else "unknown" if x.state == "UNKNOWN" else "visible"
        rows.append({
            "saddle_no": s, "state_kind": kind, "state": key[0] if kind == "overlay" else x.state,
            "covered": x.covered, "lead_uncovered_outside": x.lead_uncovered_outside,
            "lead_uncovered_outside_ambiguous": x.lead_uncovered_outside_ambiguous,
            "tier_attr": x.tier_attr if kind == "base" else None,
            "end_attr": key[1] if kind == "overlay" and key[0] == "DETACHED" else None,
            "method": "cv_extract", "t_start_frac": fs, "t_end_frac": fe,
            "confidence": sum(fr[i].conf for i in range(a, b + 1)) / (b - a + 1),
            "visibility": vis,
            "start_truncated": first_in_iv and abs(iv_a - t0) > 1e-9,
            "end_truncated": last_in_iv and abs(iv_b - tend) > 1e-9,
        })

    # base segments: consecutive frames with equal key inside one interval
    a = None
    for i in range(n + 1):
        k = iv_idx[i] if i < n else None
        if a is not None and (i == n or k != iv_idx[a] or base_key(i) != base_key(a)):
            emit("base", base_key(a), a, i - 1)
            a = None
        if i < n and a is None and k is not None:
            a = i
    # overlays
    active: dict[tuple, int] = {}
    for i in range(n + 1):
        k = iv_idx[i] if i < n else None
        now = overlay_keys(i) if (i < n and k is not None) else set()
        for key, start in list(active.items()):
            if key not in now or k != iv_idx[start]:
                emit("overlay", key, start, i - 1)
                del active[key]
        for key in now:
            if key not in active:
                active[key] = i
    return rows
