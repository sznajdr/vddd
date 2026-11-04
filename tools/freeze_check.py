#!/usr/bin/env python3
"""D-36 promotion check. Exit 0 only when the 2.0.0 freeze is allowed.

Blocks on: any evidence_gated.yaml entry with instantiated: false; any kill gate not `pass`
(KG-5 is advisory: reported, not blocking, because it is a project gate, not a spec gate);
SPEC_STATUS already FROZEN while markers remain (inconsistent state).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.version import SPEC_STATUS

ADVISORY_GATES = {"KG-5"}


def main() -> int:
    eg = yaml.safe_load((ROOT / "spec/registers/evidence_gated.yaml").read_text(encoding="utf-8"))
    kg = yaml.safe_load((ROOT / "spec/registers/kill_gates.yaml").read_text(encoding="utf-8"))
    problems: list[str] = []
    for e in eg["entries"]:
        if not e.get("instantiated"):
            problems.append(f"EG not instantiated: {e['key']} (provisional {e.get('provisional')})")
        elif e.get("value") is None or not e.get("evidence"):
            problems.append(f"EG instantiated without value/evidence: {e['key']}")
    advisories: list[str] = []
    for g in kg["gates"]:
        if g["status"] == "pass":
            continue
        msg = f"kill-gate {g['id']} ({g['name']}): {g['status']}"
        (advisories if g["id"] in ADVISORY_GATES else problems).append(msg)
    if SPEC_STATUS == "FROZEN" and problems:
        problems.insert(0, "SPEC_STATUS is FROZEN but markers remain — inconsistent")

    print(f"spec status: {SPEC_STATUS}")
    for a in advisories:
        print(f"ADVISORY  {a}")
    if problems:
        print(f"FREEZE BLOCKED — {len(problems)} item(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("FREEZE ALLOWED: all EG entries instantiated, kill-gates pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
