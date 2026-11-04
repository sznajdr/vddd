"""BORIS (Friard & Gamba 2016) aggregated-events export -> hand_charts + events rows (RP-17; §5.2; §9).

Ethogram convention (documented in protocols/HAND-CHARTING/PROTOCOL.md):
  subjects   : saddle numbers as strings ("1".."14") and "camera"
  anchors    : point events T0 and TEND (any subject)
  base states: LEADER, POCKET, RAIL_COVERED, RAIL_UNCOVERED, OUTSIDE_COVERED, PARKED, WIDE,
               NOT_VISIBLE, UNKNOWN as STATE events; WIDE needs modifiers "tier:N" and
               "covered"|"uncovered"; PARKED may carry "lead" or "lead_ambiguous"
  overlays   : DETACHED (state, modifier front|rear), BREAKING (state)
  events     : BREAK (point, modifiers recovered|not_recovered|unknown), SHOT_GAP (state on subject
               "camera", modifier = comma-separated shot types in order)
Column names follow BORIS's aggregated export; `columns` can remap them.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from itertools import pairwise

BASE = {"LEADER": False, "POCKET": True, "RAIL_COVERED": True, "RAIL_UNCOVERED": False,
        "OUTSIDE_COVERED": True, "PARKED": False}
ABSTAIN = {"NOT_VISIBLE", "UNKNOWN"}
DEFAULT_COLUMNS = {"subject": "Subject", "behavior": "Behavior", "type": "Behavior type",
                   "start": "Start (s)", "stop": "Stop (s)", "modifiers": "Modifiers", "comment": "Comment start"}


@dataclass(frozen=True)
class BorisEvent:
    subject: str
    behavior: str
    kind: str              # STATE | POINT
    start: float
    stop: float | None
    modifiers: tuple[str, ...]
    comment: str = ""


def parse_boris_export(text: str, columns: dict[str, str] | None = None) -> list[BorisEvent]:
    cols = dict(DEFAULT_COLUMNS, **(columns or {}))
    delim = "\t" if text.splitlines()[0].count("\t") > text.splitlines()[0].count(",") else ","
    rd = csv.DictReader(io.StringIO(text), delimiter=delim)
    header = {h.strip().lower(): h for h in rd.fieldnames or []}

    def col(key: str) -> str | None:
        want = cols[key].strip().lower()
        return header.get(want)

    out = []
    for r in rd:
        beh = (r.get(col("behavior") or "", "") or "").strip()
        if not beh:
            continue
        kind = (r.get(col("type") or "", "") or "STATE").strip().upper()
        start = float(r[col("start")])
        stop_raw = r.get(col("stop") or "", "")
        stop = float(stop_raw) if (stop_raw not in (None, "", "NA") and kind == "STATE") else None
        mods = tuple(m.strip() for m in (r.get(col("modifiers") or "", "") or "").replace("|", ",").split(",") if m.strip())
        out.append(BorisEvent((r.get(col("subject") or "", "") or "").strip(), beh, "POINT" if kind.startswith("POINT") else "STATE",
                              start, stop, mods, (r.get(col("comment") or "", "") or "").strip()))
    return out


def boris_to_hand_charts(events: list[BorisEvent], race_id: str, split: str,
                         charter_minutes: float | None = None) -> dict:
    """Returns {'anchors': {...}, 'hand_charts': [...], 'events': [...], 'problems': [...]}.
    Rows carry no seg_id/event_id (assign with m8_storage.ordinal_ids) and no version columns."""
    problems: list[str] = []
    t0 = next((e.start for e in events if e.behavior == "T0"), None)
    tend = next((e.start for e in events if e.behavior == "TEND"), None)
    if t0 is None or tend is None or tend <= t0:
        return {"anchors": None, "hand_charts": [], "events": [], "problems": ["T0/TEND point events missing or inverted"]}

    def frac(t: float) -> float:
        return (t - t0) / (tend - t0)

    gaps: list[tuple[float, float, list[str]]] = []
    for e in events:
        if e.behavior == "SHOT_GAP" and e.kind == "STATE" and e.stop is not None:
            gaps.append((frac(e.start), frac(e.stop), [m for m in e.modifiers] or ["other"]))
    gaps.sort()

    rows: list[dict] = []
    ev_rows: list[dict] = [{
        "race_id": race_id, "saddle_no": 0, "type": "SHOT_GAP", "t_start_frac": max(0.0, a), "t_end_frac": min(1.0, b),
        "source_shot_types": types, "shot_type_before": None, "shot_type_after": None,
        "method": "human_chart", "review_status": "accepted", "human_confirmed": True,
    } for a, b, types in gaps if b > 0 and a < 1]

    by_runner: dict[int, list[BorisEvent]] = {}
    for e in events:
        if e.subject.isdigit():
            by_runner.setdefault(int(e.subject), []).append(e)

    for saddle, evs in sorted(by_runner.items()):
        base_rows = []
        breaking = [(frac(e.start), frac(e.stop)) for e in evs if e.behavior == "BREAKING" and e.stop is not None]
        for e in evs:
            if e.kind != "STATE" or e.stop is None:
                continue
            a, b = max(0.0, frac(e.start)), min(1.0, frac(e.stop))
            if b <= a:
                continue
            mods = set(e.modifiers)
            if e.behavior in BASE or e.behavior == "WIDE" or e.behavior in ABSTAIN:
                covered: bool | None
                tier_attr = None
                lead: bool | None = False
                lead_amb: bool | None = False
                if e.behavior in ABSTAIN:
                    covered, lead, lead_amb = None, None, None
                elif e.behavior == "WIDE":
                    tier = next((int(m.split(":")[1]) for m in mods if m.startswith("tier:")), None)
                    if tier is None or not ({"covered", "uncovered"} & mods):
                        problems.append(f"runner {saddle}: WIDE at {e.start}s needs modifiers tier:N and covered|uncovered")
                    covered, tier_attr = ("covered" in mods), tier
                elif e.behavior == "PARKED":
                    covered = False
                    if "lead_ambiguous" in mods:
                        lead, lead_amb = None, True
                    elif "lead" in mods:
                        lead = True
                else:
                    covered = BASE[e.behavior]
                vis = "not_visible" if e.behavior == "NOT_VISIBLE" else "unknown" if e.behavior == "UNKNOWN" else "visible"
                base_rows.append({
                    "race_id": race_id, "saddle_no": saddle, "state_kind": "base", "state": e.behavior, "covered": covered,
                    "lead_uncovered_outside": lead, "lead_uncovered_outside_ambiguous": lead_amb, "tier_attr": tier_attr,
                    "end_attr": None, "method": "human_chart", "t_start_frac": a, "t_end_frac": b, "confidence": None,
                    "visibility": vis, "start_truncated": any(abs(a - gb) < 1e-6 for _, gb, _ in gaps),
                    "end_truncated": any(abs(b - ga) < 1e-6 for ga, _, _ in gaps), "charter_minutes": charter_minutes, "split": split,
                })
            elif e.behavior in ("DETACHED", "BREAKING"):
                end_attr = next((m for m in mods if m in ("front", "rear")), None)
                if e.behavior == "DETACHED" and end_attr is None:
                    problems.append(f"runner {saddle}: DETACHED at {e.start}s needs modifier front|rear")
                rows.append({
                    "race_id": race_id, "saddle_no": saddle, "state_kind": "overlay", "state": e.behavior, "covered": None,
                    "lead_uncovered_outside": None, "lead_uncovered_outside_ambiguous": None, "tier_attr": None,
                    "end_attr": end_attr, "method": "human_chart", "t_start_frac": a, "t_end_frac": b, "confidence": None,
                    "visibility": "visible", "start_truncated": False, "end_truncated": False,
                    "charter_minutes": charter_minutes, "split": split,
                })
        for e in evs:
            if e.behavior == "BREAK" and e.kind == "POINT":
                s = frac(e.start)
                end = next((b for a, b in breaking if abs(a - s) < 0.01), None)
                rec = True if "recovered" in e.modifiers else False if "not_recovered" in e.modifiers else None
                if end is None and s < 1.0 and rec is True:
                    problems.append(f"runner {saddle}: BREAK at {e.start}s marked recovered but no BREAKING state starts there")
                ev_rows.append({
                    "race_id": race_id, "saddle_no": saddle, "type": "BREAK", "t_start_frac": s, "t_end_frac": end,
                    "positions_lost": None, "positions_lost_basis_n": None, "recovered": rec,
                    "method": "human_chart", "review_status": "accepted", "human_confirmed": True,
                })
        # overlap check on base rows (exactly one base segment per charted instant)
        base_rows.sort(key=lambda r: r["t_start_frac"])
        for x, y in pairwise(base_rows):
            if y["t_start_frac"] < x["t_end_frac"] - 1e-9:
                problems.append(f"runner {saddle}: overlapping base segments at {x['t_end_frac']:.3f}")
        # gap check: uncharted time must be inside a SHOT_GAP
        cursor = 0.0
        for r in base_rows + [None]:
            nxt = 1.0 if r is None else r["t_start_frac"]
            if nxt - cursor > 1e-6 and not any(ga - 1e-6 <= cursor and nxt <= gb + 1e-6 for ga, gb, _ in gaps):
                problems.append(f"runner {saddle}: uncharted interval [{cursor:.3f}, {nxt:.3f}) not covered by SHOT_GAP")
            if r is not None:
                cursor = max(cursor, r["t_end_frac"])
        rows.extend(base_rows)

    rows.sort(key=lambda r: (r["saddle_no"], r["state_kind"] != "base", r["t_start_frac"]))
    return {"anchors": {"t0_video_s": t0, "tend_video_s": tend}, "hand_charts": rows, "events": ev_rows, "problems": sorted(set(problems))}
