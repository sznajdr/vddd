"""OD-1x sheets (+ pilot reports) → proposed EG registry instantiations (RECON §4 rules; D-34, D-30, D-29, RP-5).

Pure functions; tools/instantiate_eg.py is the CLI. Every proposal carries an evidence string naming the sheet
and the rows it came from. Keys whose rule cannot be satisfied by the data are NOT proposed (they stay
un-instantiated and block the freeze) — the tool never fills a value it cannot justify.
"""
from __future__ import annotations

import csv
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

from tripstate.config import ThresholdSet

Proposal = tuple[object, str]   # (value, evidence)

PILOT_KEYS = ("dod3_median_target_min", "human_budget_cap_min")


def read_sheet(path: Path) -> list[dict]:
    """CSV rows, '#' comment lines skipped, blank rows dropped."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
    return [r for r in rows if any((v or "").strip() for v in r.values())]


def fnum(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def p95(xs: list[float]) -> float:
    xs = sorted(xs)
    if len(xs) == 1:
        return xs[0]
    k = 0.95 * (len(xs) - 1)
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _truthy(x) -> bool:
    return (x or "").strip().lower() in ("1", "true", "yes")


def propose_from_sheets(sheets_dir: Path, ts: ThresholdSet) -> tuple[dict[str, Proposal], list[str]]:
    """Returns (proposals, warnings)."""
    d = Path(sheets_dir)
    proposed: dict[str, Proposal] = {}
    warnings: list[str] = []

    # Anchors (D-34): per start type, offset = median residual, tol = max(0.5, ~p95 |residual - offset|)
    by_type: dict[str, list[float]] = defaultdict(list)
    anchors = read_sheet(d / "sheet_anchors.csv")
    for r in anchors:
        t0, te, off = fnum(r.get("t0_video_s")), fnum(r.get("tend_video_s")), fnum(r.get("official_elapsed_norm_s"))
        if None in (t0, te, off):
            continue
        by_type[r["start_type"].strip()].append((te - t0) - off)
    for stype, res in by_type.items():
        offset = st.median(res)
        tol = max(0.5, p95([abs(x - offset) for x in res]))
        proposed[f"anchor_offset_{stype}_s"] = (round(offset, 3), f"sheet_anchors.csv n={len(res)}")
        proposed[f"anchor_tol_{stype}_s"] = (round(tol, 3), f"sheet_anchors.csv n={len(res)} (max(0.5, ~p95 |res-offset|))")

    # Coverage (Q-1/Q-2) — sanity: do all races clear the provisional gates?
    cov = read_sheet(d / "sheet_coverage.csv")
    if cov:
        per_race: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
        for r in cov:
            s, e = fnum(r.get("t_start_video_s")), fnum(r.get("t_end_video_s"))
            if s is not None and e is not None:
                per_race[r["race_id"]].append((s, e, r["shot_type"].strip()))
        anchor_by: dict[str, tuple[float | None, float | None]] = {}
        for r in anchors:   # first pass per race defines the window
            anchor_by.setdefault(r["race_id"], (fnum(r.get("t0_video_s")), fnum(r.get("tend_video_s"))))
        rates, thirds = [], []
        for rid, shots in per_race.items():
            t0, te = anchor_by.get(rid, (None, None))
            if t0 is None or te is None:
                continue

            def frac(lo: float, hi: float, shots=shots) -> float | None:
                tot = hi - lo
                wp = sum(max(0.0, min(e, hi) - max(s, lo)) for s, e, t in shots if t == "wide_pan")
                return wp / tot if tot > 0 else None
            rates.append(frac(t0, te))
            thirds.append(frac(t0 + 2 * (te - t0) / 3, te))
        rates = [x for x in rates if x is not None]
        thirds = [x for x in thirds if x is not None]
        if rates:
            proposed["coverage_race_min"] = (ts["coverage_race_min"], f"sheet_coverage.csv observed min={min(rates):.3f} over {len(rates)} races; gate kept iff all clear")
            proposed["coverage_final_third_min"] = (ts["coverage_final_third_min"], f"sheet_coverage.csv observed min={min(thirds):.3f}")
            if min(rates) < float(ts["coverage_race_min"]) or min(thirds) < float(ts["coverage_final_third_min"]):
                warnings.append("coverage: at least one OD-1x replay fails the provisional Q-1/Q-2 gate; the registry rule says the gate or corpus definition is revisited before charting")

    # Geometry (RP-5, F-1, F-3)
    geo = read_sheet(d / "sheet_geometry.csv")
    if geo:
        swr = float(ts["sw_ratio"])
        lane_sw = [fnum(r.get("lane_gap_in_sl")) / swr for r in geo if fnum(r.get("lane_gap_in_sl"))]
        cov_sw = [fnum(r.get("cover_lat_in_sl")) / swr for r in geo if fnum(r.get("cover_lat_in_sl"))]
        by_loc: dict[str, list[float]] = defaultdict(list)
        for r in geo:
            v = fnum(r.get("lane_gap_in_sl"))
            if v:
                by_loc[r["location"].strip()].append(v)
        if lane_sw:
            proposed["same_tier_sw"] = (ts["same_tier_sw"], f"sheet_geometry.csv adjacent-lane gap in SW: min={min(lane_sw):.2f} median={st.median(lane_sw):.2f}; OK iff min > same_tier_sw")
            proposed["max_tier_span_sw"] = (ts["max_tier_span_sw"], "sheet_geometry.csv sanity")
            if min(lane_sw) <= float(ts["same_tier_sw"]):
                warnings.append("geometry: an adjacent-lane gap is not above same_tier_sw; the tiering key set needs recalibration before M4 work (RP-5)")
        if cov_sw:
            proposed["cover_lat_sw"] = (round(max(cov_sw) + 0.1, 2), f"sheet_geometry.csv real cover positions in SW: max={max(cov_sw):.2f}; set to max+0.1")
        if len(by_loc) >= 2:
            meds = {k: st.median(v) for k, v in by_loc.items()}
            ratio = max(meds.values()) / min(meds.values())
            proposed["sw_ratio_location_variation"] = (round(ratio, 2), f"sheet_geometry.csv lane-gap/SL medians by location {meds}; >2.0 triggers RP-5")
            if ratio <= 2.0:
                proposed["sw_ratio"] = (ts["sw_ratio"], f"sheet_geometry.csv location variation {ratio:.2f} <= 2.0: provisional sw_ratio confirmed (RP-5 not triggered)")
            else:
                warnings.append(f"geometry: lane-gap/SL varies {ratio:.2f}x across locations (> 2.0): RP-5 per-shot sw_ratio is an owner decision; sw_ratio NOT instantiated")
        n6 = sum(1 for r in geo if _truthy(r.get("gap_ge_6sl_seen")))
        proposed["detach_sl_prevalence"] = (n6, f"sheet_geometry.csv frames with >=6 SL gap: {n6}/{len(geo)}")
        # axis_neighbourhood_k: stays 0 unless the bend frame shows > 0.5 SW axis-induced error (research 05).
        bend_err = [fnum(r.get("axis_lateral_error_sw")) for r in geo if r.get("location", "").strip() == "bend"]
        bend_err = [x for x in bend_err if x is not None]
        if bend_err:
            if max(bend_err) <= 0.5:
                proposed["axis_neighbourhood_k"] = (ts["axis_neighbourhood_k"], f"sheet_geometry.csv bend frames: max axis-induced lateral error {max(bend_err):.2f} SW <= 0.5; k stays {ts['axis_neighbourhood_k']}")
            else:
                warnings.append(f"geometry: bend frame shows {max(bend_err):.2f} SW axis-induced lateral error (> 0.5): axis_neighbourhood_k needs the smallest k that removes it (owner/agent study); NOT instantiated")
        else:
            warnings.append("geometry: no axis_lateral_error_sw column on bend frames; axis_neighbourhood_k not instantiated (RP-20: with a rail datum it is a sanity key only)")
        # track_width_sl: only when a frame reads both lines (fence_rail_px / sl_px) or a track plan is given.
        widths = [fnum(r.get("fence_rail_px")) / fnum(r.get("sl_px")) for r in geo
                  if fnum(r.get("fence_rail_px")) and fnum(r.get("sl_px")) and _truthy(r.get("both_lines_visible"))
                  and r.get("location", "").strip() in ("near_straight",)]
        if widths:
            proposed["track_width_sl"] = (round(st.median(widths), 2), f"sheet_geometry.csv near-straight frames with both lines visible: fence-rail / SL median over {len(widths)} frames (perspective-uncorrected; replace by the track plan when known)")
        else:
            warnings.append("geometry: no near-straight frame with both lines visible; track_width_sl not instantiated (needs the track plan or OD-1x step 4.6)")

    # Finish (D-30)
    fin = read_sheet(d / "sheet_finish.csv")
    if fin:
        ks = [int(fnum(r.get("n_identifiable")) or 0) for r in fin]
        unamb = all(_truthy(r.get("order_unambiguous")) for r in fin)
        k = int(ts["finish_evidence_min_k"])
        if min(ks) < k and unamb:
            k = max(1, min(ks))
        proposed["finish_evidence_min_k"] = (k, f"sheet_finish.csv identifiable crossings per race {ks}; order unambiguous={unamb}")

    # Seeding (KG-1)
    seed = read_sheet(d / "sheet_seeding.csv")
    first = [fnum(r.get("seconds_elapsed")) for r in seed if (r.get("attempt") or "").strip() == "1"]
    first = [x for x in first if x is not None]
    if first:
        proposed["seeding_feasible"] = (round(st.median(first) / 60, 2), f"sheet_seeding.csv median first-frame seeding minutes over {len(first)} races; KG-1 threshold 8")

    # Race sheet: native fps of the replays (normalized_fps)
    race = read_sheet(d / "sheet_race.csv")
    fps = sorted({fnum(r.get("fps")) for r in race if fnum(r.get("fps"))})
    if len(fps) == 1:
        proposed["normalized_fps"] = (fps[0], f"sheet_race.csv native fps {fps[0]} on all {len(race)} replays")
    elif len(fps) > 1:
        warnings.append(f"race sheet: replays differ in native fps {fps}; normalized_fps is an owner decision, NOT instantiated")

    return proposed, warnings


def propose_from_pilot(reports: list[dict], ts: ThresholdSet) -> tuple[dict[str, Proposal], list[str]]:
    """D-29: DoD-3 target = pilot median human-minutes rounded up; Q-7 cap = ~p90 rounded up, raised to
    >= 1.5 x target when the pilot's p90 sits below it. Same p90 convention as tripstate.pilot.report."""
    hm = sorted(float(r["human_minutes"]) for r in reports if r.get("human_minutes") is not None)
    if not hm:
        return {}, ["pilot: no human_minutes in the reports; dod3_median_target_min / human_budget_cap_min not instantiated"]
    target = math.ceil(st.median(hm))
    p90 = hm[int(0.9 * (len(hm) - 1))]
    cap = math.ceil(p90)
    note = ""
    if cap < 1.5 * target:
        cap = math.ceil(1.5 * target)
        note = f"; raised to ceil(1.5 x target) because p90 {p90} < 1.5 x {target}"
    return {
        "dod3_median_target_min": (target, f"pilot reports n={len(hm)}: median human-minutes {st.median(hm)} -> ceil"),
        "human_budget_cap_min": (cap, f"pilot reports n={len(hm)}: p90 human-minutes {p90} -> ceil{note}"),
    }, []


def apply_proposals(registry: dict, proposed: dict[str, Proposal], date: str) -> list[str]:
    """Fill matching registry entries in place; returns the keys that were updated."""
    done = []
    for e in registry["entries"]:
        if e["key"] in proposed:
            v, ev = proposed[e["key"]]
            e.update(instantiated=True, value=v, evidence=ev, date=date)
            done.append(e["key"])
    return done
