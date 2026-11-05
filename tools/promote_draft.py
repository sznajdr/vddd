#!/usr/bin/env python3
"""D-36 promotion: spec/SPEC-2.0.0-draft.md → spec/SPEC-2.0.0.md (FROZEN) in one command.

  promote_draft.py                       real run on the repository (refuses unless tools/freeze_check.py passes)
  promote_draft.py --dry-run --registry R.yaml --kill-gates K.yaml [--strip-open-markers] [--out-dir DIR]
                                         simulate with another registry / kill-gates file; writes the four outputs,
                                         their diffs and promotion-report.md into DIR (default: a fresh temp dir)

Real run writes: spec/SPEC-2.0.0.md, config/thresholds/TS-2.0.0-frozen.yaml, spec/decisions/DECISION-LOG.md
(D-26…D-36 → Closed), src/tripstate/version.py (SPEC_VERSION 2.0.0, FROZEN). The draft, its ledger and
tools/cut_draft.py stay as history. A second real run says "already frozen" and changes nothing.
Logic: tripstate.release.promote. DO NOT run the real promotion before OD-1x and the pilot (D-36).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from datetime import UTC
from datetime import datetime as _dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.release.freeze import KILL_GATES_PATH, REGISTRY_PATH, load_yaml
from tripstate.release.promote import PromotionInputs, PromotionRefused, promote, unified_diff
from tripstate.version import SPEC_STATUS, SPEC_VERSION

DRAFT = ROOT / "spec" / "SPEC-2.0.0-draft.md"
FROZEN = ROOT / "spec" / "SPEC-2.0.0.md"
LOG = ROOT / "spec" / "decisions" / "DECISION-LOG.md"
TS_SRC = ROOT / "config" / "thresholds" / "TS-0.0.0-provisional.yaml"
TS_DST = ROOT / "config" / "thresholds" / "TS-2.0.0-frozen.yaml"
VERSION_PY = ROOT / "src" / "tripstate" / "version.py"


def lint(spec_path: Path, registry_path: Path) -> int:
    p = subprocess.run([sys.executable, str(ROOT / "tools" / "lint_spec.py"), str(spec_path), str(registry_path)],
                       capture_output=True, text=True, cwd=ROOT, check=False)
    print(p.stdout.strip())
    return p.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--registry", default=None, help="dry run only: registry YAML to simulate with")
    ap.add_argument("--kill-gates", default=None, help="dry run only: kill-gates YAML to simulate with")
    ap.add_argument("--strip-open-markers", action="store_true", help="dry run only: pretend the [OPEN] owner decisions were resolved")
    ap.add_argument("--out-dir", default=None, help="dry run only: where the simulated outputs and diffs go")
    ap.add_argument("--date", default=_dt.now(UTC).date().isoformat())
    a = ap.parse_args()
    if not a.dry_run and (a.registry or a.kill_gates or a.strip_open_markers or a.out_dir):
        print("REFUSED: --registry / --kill-gates / --strip-open-markers / --out-dir are dry-run options; the real promotion "
              "uses the repository registers only.")
        return 2
    if not a.dry_run:
        if FROZEN.exists() and SPEC_STATUS == "FROZEN":
            print(f"already frozen: {FROZEN.relative_to(ROOT)} exists and SPEC_STATUS = FROZEN ({SPEC_VERSION}); nothing to do.")
            return 0
        if FROZEN.exists() != (SPEC_STATUS == "FROZEN"):
            print(f"REFUSED: partial promotion detected (frozen file exists: {FROZEN.exists()}, SPEC_STATUS: {SPEC_STATUS}); repair by hand.")
            return 1
    registry = load_yaml(a.registry or REGISTRY_PATH)
    gates = load_yaml(a.kill_gates or KILL_GATES_PATH)
    inp = PromotionInputs(DRAFT.read_text(encoding="utf-8"), LOG.read_text(encoding="utf-8"), TS_SRC.read_text(encoding="utf-8"),
                          VERSION_PY.read_text(encoding="utf-8"), registry, gates, a.date, strip_open=a.strip_open_markers)
    try:
        out = promote(inp)
    except PromotionRefused as e:
        print(f"REFUSED ({'dry run' if a.dry_run else 'promotion'}) — {len(e.reasons)} reason(s):")
        for r in e.reasons:
            print(f"  - {r}")
        return 1
    if a.dry_run:
        out_dir = Path(a.out_dir) if a.out_dir else Path(tempfile.mkdtemp(prefix="promote-dry-run-"))
        out_dir.mkdir(parents=True, exist_ok=True)
        files = {"SPEC-2.0.0.md": (DRAFT, out.frozen_spec), "TS-2.0.0-frozen.yaml": (TS_SRC, out.frozen_ts),
                 "DECISION-LOG.md": (LOG, out.decision_log), "version.py": (VERSION_PY, out.version_py)}
        for name, (src, text) in files.items():
            (out_dir / name).write_text(text, encoding="utf-8")
            (out_dir / (name + ".diff")).write_text(unified_diff(src.read_text(encoding="utf-8"), text, name), encoding="utf-8")
        (out_dir / "promotion-report.md").write_text(out.report_md, encoding="utf-8")
        print(out.report_md)
        print(f"dry run outputs + diffs in {out_dir}")
        rc = lint(out_dir / "SPEC-2.0.0.md", Path(a.registry or REGISTRY_PATH))
        print("DRY RUN OK — nothing in the repository was changed." if rc == 0 else "DRY RUN: lint failed on the simulated frozen file")
        return rc
    FROZEN.write_text(out.frozen_spec, encoding="utf-8")
    TS_DST.write_text(out.frozen_ts, encoding="utf-8")
    LOG.write_text(out.decision_log, encoding="utf-8")
    VERSION_PY.write_text(out.version_py, encoding="utf-8")
    (ROOT / "spec" / "PROMOTION-2.0.0-report.md").write_text(out.report_md, encoding="utf-8")
    print(out.report_md)
    rc = lint(FROZEN, REGISTRY_PATH)
    print(f"PROMOTED: wrote {FROZEN.relative_to(ROOT)}, {TS_DST.relative_to(ROOT)}, {LOG.relative_to(ROOT)}, {VERSION_PY.relative_to(ROOT)}.")
    print("Next: make test && make lint-spec && make freeze-check, then commit everything in ONE commit (D-36).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
