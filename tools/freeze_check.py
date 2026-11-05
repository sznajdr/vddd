#!/usr/bin/env python3
"""D-36 promotion check. Exit 0 only when the 2.0.0 freeze is allowed.

Blocks on: any evidence_gated.yaml entry with instantiated: false; any kill gate KG-1…KG-4 not `pass`
(KG-5 is advisory: reported, not blocking, because it is a project gate, not a spec gate); any `[EG]` marker
in the draft that binds to no registry entry; any `[OPEN]` owner decision left in the draft; SPEC_STATUS
already FROZEN while markers remain (inconsistent state). Logic lives in tripstate.release.freeze so that
tools/promote_draft.py applies exactly the same test.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.release.freeze import check_repo, render
from tripstate.version import SPEC_STATUS


def main() -> int:
    report = check_repo()
    print(render(report, SPEC_STATUS))
    return 0 if report.allowed else 1


if __name__ == "__main__":
    raise SystemExit(main())
