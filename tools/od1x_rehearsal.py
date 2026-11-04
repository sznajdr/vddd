#!/usr/bin/env python3
"""OD-1x rehearsal (backlog C6): one clean-checkout command that walks the owner's afternoon with synthetic inputs,
so there are no tooling surprises on the real day. Nothing it writes is evidence; everything lands in --out.

  od1x_rehearsal.py --out /tmp/tripstate-od1x-rehearsal [--duration 8] [--skip-video]

Steps:
  1. synthetic clip + truth + seed script (tools/synth_video.py) → <out>/synth/           [needs ffmpeg]
  2. clean sheet templates (protocols/OD-1x/sheets/*.csv)    → <out>/od1x/             what the owner copies to data/od1x/
  3. scripted stopwatch example (tools/od1x_timer.py --script) → <out>/od1x/sheet_seeding.csv (row marked REHEARSAL)
  4. instantiation dry run on the committed synthetic sheets (tests/fixtures/od1x_synthetic) + pilot reports:
     prints the proposals exactly as tools/instantiate_eg.py would, and checks them against the fixture expectations.
  5. prints the real-day commands from protocols/OD-1x/PROTOCOL.md.
Exit 1 if any step fails or the proposals differ from the fixture expectations.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.config import load_default
from tripstate.release.instantiate import propose_from_pilot, propose_from_sheets

FIXTURE = ROOT / "tests" / "fixtures" / "od1x_synthetic"
SHEETS = ROOT / "protocols" / "OD-1x" / "sheets"
EXPECTED = FIXTURE / "expected_proposals.json"


def fixture_proposals() -> tuple[dict, list[str]]:
    ts = load_default()
    proposed, warnings = propose_from_sheets(FIXTURE, ts)
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((FIXTURE / "pilot_reports").glob("*.json"))]
    pp, pw = propose_from_pilot(reports, ts)
    proposed.update(pp)
    return {k: {"value": v, "evidence": ev} for k, (v, ev) in proposed.items()}, warnings + pw


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--duration", type=float, default=8.0)
    ap.add_argument("--skip-video", action="store_true", help="skip step 1 (no ffmpeg)")
    a = ap.parse_args()
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    py = sys.executable

    print("== 1. synthetic clip")
    if a.skip_video:
        print("   skipped (--skip-video)")
    else:
        r = subprocess.run([py, str(ROOT / "tools/synth_video.py"), "--out", str(out / "synth"), "--duration", str(a.duration)],
                           capture_output=True, text=True, check=False)
        print("   " + (r.stdout.strip().splitlines() or ["(no output)"])[-1])
        if r.returncode != 0:
            print(r.stderr)
            return 1

    print("== 2. sheet templates → " + str(out / "od1x"))
    (out / "od1x").mkdir()
    for p in sorted(SHEETS.glob("*.csv")):
        shutil.copy(p, out / "od1x" / p.name)
        print(f"   {p.name}")

    print("== 3. scripted stopwatch example (REHEARSAL row)")
    answers = {"video_timecode_s": 66.0, "wait_s": 0.1, "n_assigned": 7, "n_unassigned": 0, "n_wrong_after_check": 0,
               "id_cues": "cloth;position", "notes": "rehearsal on the synthetic clip"}
    (out / "timer_answers.json").write_text(json.dumps(answers, indent=1), encoding="utf-8")
    r = subprocess.run([py, str(ROOT / "tools/od1x_timer.py"), "--race", "SYNTH-REHEARSAL", "--attempt", "1",
                        "--sheet", str(out / "od1x" / "sheet_seeding.csv"), "--script", str(out / "timer_answers.json")],
                       capture_output=True, text=True, check=False)
    print("   " + " | ".join(r.stdout.strip().splitlines()))
    if r.returncode != 0:
        print(r.stderr)
        return 1
    with (out / "od1x" / "sheet_seeding.csv").open(encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(line for line in f if not line.startswith("#")) if row.get("race_id")]
    if not rows or not rows[-1]["notes"].startswith("REHEARSAL"):
        print("   timer row missing or not marked REHEARSAL")
        return 1

    print("== 4. instantiation dry run on tests/fixtures/od1x_synthetic (+ pilot reports)")
    proposals, warnings = fixture_proposals()
    for k, v in proposals.items():
        print(f"   {k:32s} = {v['value']!r:12}  <- {v['evidence']}")
    for w in warnings:
        print(f"   WARNING {w}")
    (out / "fixture_proposals.json").write_text(json.dumps(proposals, indent=1), encoding="utf-8")
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    diff = {k: (proposals.get(k, {}).get("value"), v) for k, v in expected.items() if proposals.get(k, {}).get("value") != v}
    extra = sorted(set(proposals) - set(expected))
    if diff or extra or warnings:
        print(f"   MISMATCH vs {EXPECTED.relative_to(ROOT)}: differing {diff}, unexpected keys {extra}, warnings {warnings}")
        return 1
    print(f"   matches {EXPECTED.relative_to(ROOT)} ({len(expected)} keys)")

    print("== 5. on the real day (protocols/OD-1x/PROTOCOL.md):")
    print("   cp protocols/OD-1x/sheets/*.csv data/od1x/        # fill them during the afternoon")
    print("   python tools/od1x_timer.py --race <race_id> --attempt 1 --sheet data/od1x/sheet_seeding.csv")
    print("   python tools/instantiate_eg.py data/od1x --ts config/thresholds/TS-0.0.0-provisional.yaml --out spec/registers/evidence_gated.yaml --dry-run")
    print("   (after the pilot) python tools/instantiate_eg.py data/od1x --pilot-reports 'data/pilot5/*/report_*.json' --out spec/registers/evidence_gated.yaml")
    print("   python tools/freeze_check.py")
    print(f"REHEARSAL OK — outputs in {out} (not evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
