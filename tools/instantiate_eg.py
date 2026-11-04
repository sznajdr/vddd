#!/usr/bin/env python3
"""Turn OD-1x sheets (+ pilot reports) into proposed EG registry values (RECON §4 rules). Dry-run prints only.

usage: instantiate_eg.py data/od1x --ts config/thresholds/TS-0.0.0-provisional.yaml \
         --out spec/registers/evidence_gated.yaml [--registry TEMPLATE.yaml] [--pilot-reports 'data/pilot5/*/report_*.json']
         [--dry-run] [--date YYYY-MM-DD]

Sheets read (comment lines starting with '#' are skipped):
  sheet_race.csv, sheet_anchors.csv, sheet_coverage.csv, sheet_geometry.csv, sheet_finish.csv, sheet_seeding.csv
Values that need the 5-race pilot (human_budget_cap_min, dod3_median_target_min) come from --pilot-reports (D-29)
and are left alone without it. Keys the data cannot justify are not proposed and keep blocking the freeze.
Logic: tripstate.release.instantiate.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from datetime import UTC
from datetime import datetime as _dt
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.config import ThresholdSet
from tripstate.release.instantiate import apply_proposals, propose_from_pilot, propose_from_sheets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sheets_dir")
    ap.add_argument("--ts", default="config/thresholds/TS-0.0.0-provisional.yaml")
    ap.add_argument("--out", default="spec/registers/evidence_gated.yaml")
    ap.add_argument("--registry", default=None, help="registry template to fill (default: --out)")
    ap.add_argument("--pilot-reports", default=None, help="glob of pilot report JSONs (human_minutes -> D-29 keys)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", default=_dt.now(UTC).date().isoformat())
    a = ap.parse_args()
    ts = ThresholdSet.load(a.ts)
    proposed, warnings = propose_from_sheets(Path(a.sheets_dir), ts)
    if a.pilot_reports:
        reports = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sorted(glob.glob(a.pilot_reports))]
        pp, pw = propose_from_pilot(reports, ts)
        proposed.update(pp)
        warnings += pw
    if not proposed:
        print("no sheets with data found in", a.sheets_dir)
        return 1
    print("Proposed EG instantiations:")
    for k, (v, ev) in proposed.items():
        print(f"  {k:32s} = {v!r:12}  <- {ev}")
    for w in warnings:
        print(f"WARNING  {w}")
    if a.dry_run:
        return 0
    src = Path(a.registry or a.out)
    reg = yaml.safe_load(src.read_text(encoding="utf-8"))
    done = apply_proposals(reg, proposed, a.date)
    Path(a.out).write_text(yaml.safe_dump(reg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    missing = [e["key"] for e in reg["entries"] if not e.get("instantiated")]
    print(f"wrote {a.out}: {len(done)} entries instantiated; still open: {missing or 'none'}")
    print("review the diff, then commit sheets + registry together.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
