#!/usr/bin/env python3
"""Convert a BORIS aggregated-events export into hand_charts/events JSON (RP-17).

  boris_to_hand_charts.py export.tsv --race 20261103-R1-C4 --split dev --minutes 14 --out data/golden/hand_charts/20261103-R1-C4.json
Exit 1 when the chart has problems (overlaps, uncharted gaps without SHOT_GAP, missing modifiers).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.charting import boris_to_hand_charts, parse_boris_export
from tripstate.m8_storage import ordinal_ids


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("export"); ap.add_argument("--race", required=True); ap.add_argument("--split", required=True, choices=["dev", "heldout"])
    ap.add_argument("--minutes", type=float); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = boris_to_hand_charts(parse_boris_export(Path(a.export).read_text(encoding="utf-8")), a.race, a.split, a.minutes)
    for p in res["problems"]:
        print("PROBLEM:", p)
    res["hand_charts"] = ordinal_ids(res["hand_charts"], "seg_id", "t_start_frac")
    res["events"] = ordinal_ids(res["events"], "event_id", "t_start_frac")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {a.out}: {len(res['hand_charts'])} segments, {len(res['events'])} events, {len(res['problems'])} problems")
    return 1 if res["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
