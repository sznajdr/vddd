#!/usr/bin/env python3
"""Turn OD-1x sheets into proposed EG registry values (RECON §4 rules). Dry-run prints only.

usage: instantiate_eg.py data/od1x --ts config/thresholds/TS-0.0.0-provisional.yaml \
         --out spec/registers/evidence_gated.yaml [--dry-run] [--date YYYY-MM-DD]

Sheets read (comment lines starting with '#' are skipped):
  sheet_anchors.csv, sheet_coverage.csv, sheet_geometry.csv, sheet_finish.csv, sheet_seeding.csv
Values that need the 5-race pilot (human_budget_cap_min, dod3_median_target_min) are left alone.
"""
from __future__ import annotations

import argparse
import csv
import statistics as st
import sys
from collections import defaultdict
from datetime import UTC
from datetime import datetime as _dt
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.config import ThresholdSet


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(l for l in f if not l.startswith("#"))]
    return [r for r in rows if any(v.strip() for v in r.values() if v)]


def fnum(x):
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheets_dir")
    ap.add_argument("--ts", default="config/thresholds/TS-0.0.0-provisional.yaml")
    ap.add_argument("--out", default="spec/registers/evidence_gated.yaml")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", default=_dt.now(UTC).date().isoformat())
    a = ap.parse_args()
    d = Path(a.sheets_dir)
    ts = ThresholdSet.load(a.ts)
    proposed: dict[str, tuple[object, str]] = {}

    # Anchors (D-34)
    by_type: dict[str, list[float]] = defaultdict(list)
    for r in read(d / "sheet_anchors.csv"):
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
    cov = read(d / "sheet_coverage.csv")
    if cov:
        per_race: dict[str, list[tuple[float, float, str]]] = defaultdict(list)
        for r in cov:
            s, e = fnum(r.get("t_start_video_s")), fnum(r.get("t_end_video_s"))
            if s is not None and e is not None:
                per_race[r["race_id"]].append((s, e, r["shot_type"].strip()))
        anchors = {r["race_id"]: (fnum(r.get("t0_video_s")), fnum(r.get("tend_video_s"))) for r in read(d / "sheet_anchors.csv")}
        rates, thirds = [], []
        for rid, shots in per_race.items():
            t0, te = anchors.get(rid, (None, None))
            if t0 is None or te is None:
                continue
            def frac(lo, hi, shots=shots):
                tot = hi - lo
                wp = sum(max(0.0, min(e, hi) - max(s, lo)) for s, e, t in shots if t == "wide_pan")
                return wp / tot if tot > 0 else None
            rates.append(frac(t0, te)); thirds.append(frac(t0 + 2 * (te - t0) / 3, te))
        if rates:
            proposed["coverage_race_min"] = (ts["coverage_race_min"], f"sheet_coverage.csv observed min={min(rates):.3f} over {len(rates)} races; gate kept iff all clear")
            proposed["coverage_final_third_min"] = (ts["coverage_final_third_min"], f"sheet_coverage.csv observed min={min(thirds):.3f}")

    # Geometry (RP-5, F-1, F-3)
    geo = read(d / "sheet_geometry.csv")
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
        if cov_sw:
            proposed["cover_lat_sw"] = (round(max(cov_sw) + 0.1, 2), f"sheet_geometry.csv real cover positions in SW: max={max(cov_sw):.2f}; set to max+0.1")
        if len(by_loc) >= 2:
            meds = {k: st.median(v) for k, v in by_loc.items()}
            ratio = max(meds.values()) / min(meds.values())
            proposed["sw_ratio_location_variation"] = (round(ratio, 2), f"sheet_geometry.csv lane-gap/SL medians by location {meds}; >2.0 triggers RP-5")
        n6 = sum(1 for r in geo if (r.get("gap_ge_6sl_seen") or "").strip().lower() in ("1", "true", "yes"))
        proposed["detach_sl_prevalence"] = (n6, f"sheet_geometry.csv frames with >=6 SL gap: {n6}/{len(geo)}")

    # Finish (D-30)
    fin = read(d / "sheet_finish.csv")
    if fin:
        ks = [int(fnum(r.get("n_identifiable")) or 0) for r in fin]
        unamb = all((r.get("order_unambiguous") or "").strip().lower() in ("1", "true", "yes") for r in fin)
        k = int(ts["finish_evidence_min_k"])
        if min(ks) < k and unamb:
            k = max(1, min(ks))
        proposed["finish_evidence_min_k"] = (k, f"sheet_finish.csv identifiable crossings per race {ks}; order unambiguous={unamb}")

    # Seeding (KG-1)
    seed = read(d / "sheet_seeding.csv")
    first = [fnum(r.get("seconds_elapsed")) for r in seed if (r.get("attempt") or "").strip() == "1"]
    first = [x for x in first if x is not None]
    if first:
        proposed["seeding_feasible"] = (round(st.median(first) / 60, 2), f"sheet_seeding.csv median first-frame seeding minutes over {len(first)} races; KG-1 threshold 8")

    if not proposed:
        print("no sheets with data found in", d)
        return 1
    print("Proposed EG instantiations:")
    for k, (v, ev) in proposed.items():
        print(f"  {k:32s} = {v!r:12}  <- {ev}")
    if a.dry_run:
        return 0
    reg = yaml.safe_load(Path(a.out).read_text(encoding="utf-8"))
    for e in reg["entries"]:
        if e["key"] in proposed:
            v, ev = proposed[e["key"]]
            e.update(instantiated=True, value=v, evidence=ev, date=a.date)
    Path(a.out).write_text(yaml.safe_dump(reg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"wrote {a.out}; review the diff, then commit sheets + registry together.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
