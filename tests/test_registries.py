"""The registries must agree with each other, and the freeze must be blocked right now."""
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_eg_keys_exist_in_threshold_set(ts):
    eg = yaml.safe_load((ROOT / "spec/registers/evidence_gated.yaml").read_text())
    named_checks = {"sw_ratio_location_variation", "detach_sl_prevalence", "seeding_feasible"}  # not threshold keys
    for e in eg["entries"]:
        if e["key"] in named_checks:
            continue
        assert e["key"] in ts.thresholds, e["key"]
        assert ts.thresholds[e["key"]].eg, f"{e['key']} must be flagged eg: true in the TS"


def test_every_eg_flagged_threshold_is_in_registry(ts):
    eg = yaml.safe_load((ROOT / "spec/registers/evidence_gated.yaml").read_text())
    keys = {e["key"] for e in eg["entries"]}
    missing = [k for k in ts.evidence_gated_keys() if k not in keys]
    assert not missing, missing


def test_freeze_check_blocks_now():
    p = subprocess.run([sys.executable, str(ROOT / "tools/freeze_check.py")], capture_output=True, text=True, cwd=ROOT, check=False)
    assert p.returncode == 1
    assert "BLOCKED" in p.stdout
