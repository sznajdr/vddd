#!/usr/bin/env python3
"""Aggregate pilot race reports -> pilot_report.md and kill_gates.yaml statuses (KG-1…KG-4).

  pilot_report.py --reports 'data/pilot5/*/report_*.json' --md data/pilot5/pilot_report.md \
                  [--kill-gates spec/registers/kill_gates.yaml] [--anchors data/od1x/sheet_anchors.csv]
Without --kill-gates the registry is left untouched (dry run).
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.config import load_default
from tripstate.pilot.report import (
    aggregate,
    evaluate_kill_gates,
    markdown,
    write_kill_gates,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", required=True); ap.add_argument("--md", required=True)
    ap.add_argument("--kill-gates"); ap.add_argument("--anchors")
    a = ap.parse_args()
    reports = [json.loads(Path(p).read_text()) for p in sorted(glob.glob(a.reports))]
    if not reports:
        print("no reports matched"); return 1
    residuals: dict[str, list[float]] = defaultdict(list)
    if a.anchors:
        with open(a.anchors, newline="") as f:
            for r in csv.DictReader(line for line in f if not line.startswith("#")):
                try:
                    residuals[r["start_type"].strip()].append(float(r["tend_video_s"]) - float(r["t0_video_s"]) - float(r["official_elapsed_norm_s"]))
                except (KeyError, ValueError):
                    continue
    ts = load_default()
    tol = {"volte": float(ts["anchor_tol_volte_s"]), "autostart": float(ts["anchor_tol_autostart_s"])}
    agg = aggregate(reports, anchor_residuals=dict(residuals) or None, provisional_tol=tol)
    status = write_kill_gates(Path(a.kill_gates), agg, f"{len(reports)} pilot reports via tools/pilot_report.py") if a.kill_gates else evaluate_kill_gates(agg)
    Path(a.md).parent.mkdir(parents=True, exist_ok=True)
    Path(a.md).write_text(markdown(agg, status), encoding="utf-8")
    print(markdown(agg, status))
    print("kill_gates.yaml updated" if a.kill_gates else "dry run: kill_gates.yaml untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
