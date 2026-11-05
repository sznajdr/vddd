"""A5 — D-36 promotion mechanics on the synthetic OD-1x fixture (SPEC-2.0.0-draft handoff §2).

The real promotion MUST NOT run before OD-1x and the pilot; these tests run it only on an isolated copy
of the repository and on in-memory texts."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tripstate.config import ThresholdSet, load_default
from tripstate.release.freeze import check_freeze
from tripstate.release.instantiate import apply_proposals, propose_from_pilot, propose_from_sheets
from tripstate.release.markers import bind_markers, strip_open_markers
from tripstate.release.promote import PENDING_IDS, PromotionInputs, PromotionRefused, promote

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "od1x_synthetic"
DRAFT = (ROOT / "spec" / "SPEC-2.0.0-draft.md").read_text(encoding="utf-8")
LOG = (ROOT / "spec" / "decisions" / "DECISION-LOG.md").read_text(encoding="utf-8")
TS_TEXT = (ROOT / "config" / "thresholds" / "TS-0.0.0-provisional.yaml").read_text(encoding="utf-8")
VERSION_PY = (ROOT / "src" / "tripstate" / "version.py").read_text(encoding="utf-8")
REAL_REGISTRY = yaml.safe_load((ROOT / "spec" / "registers" / "evidence_gated.yaml").read_text(encoding="utf-8"))
REAL_GATES = yaml.safe_load((ROOT / "spec" / "registers" / "kill_gates.yaml").read_text(encoding="utf-8"))
PASS_GATES = yaml.safe_load((FIX / "kill_gates_pass.yaml").read_text(encoding="utf-8"))
TEMPLATE = yaml.safe_load((FIX / "evidence_gated.template.yaml").read_text(encoding="utf-8"))


def synthetic_registry() -> dict:
    ts = load_default()
    reg = json.loads(json.dumps(TEMPLATE))
    proposed, warnings = propose_from_sheets(FIX, ts)
    reports = [json.loads(p.read_text()) for p in sorted((FIX / "pilot_reports").glob("*.json"))]
    pp, pw = propose_from_pilot(reports, ts)
    proposed.update(pp)
    assert not warnings and not pw, (warnings, pw)
    apply_proposals(reg, proposed, "2026-11-04")
    assert all(e["instantiated"] for e in reg["entries"])
    return reg


def inputs(registry, gates, strip_open=True) -> PromotionInputs:
    return PromotionInputs(DRAFT, LOG, TS_TEXT, VERSION_PY, registry, gates, "2026-11-04", strip_open=strip_open)


# --- fixture integrity ------------------------------------------------------------------------

def test_template_registry_matches_real_registry():
    real = {e["key"]: e for e in REAL_REGISTRY["entries"]}
    tmpl = {e["key"]: e for e in TEMPLATE["entries"]}
    assert set(tmpl) == set(real)
    for k, e in real.items():
        assert tmpl[k] == e, k


def test_instantiate_from_synthetic_sheets_and_pilot():
    ts = load_default()
    proposed, warnings = propose_from_sheets(FIX, ts)
    assert not warnings
    assert proposed["anchor_offset_autostart_s"][0] == 0.3 and proposed["anchor_offset_volte_s"][0] == 1.2
    assert proposed["anchor_tol_volte_s"][0] == 0.5                         # max(0.5, p95) floor
    assert proposed["cover_lat_sw"][0] == 0.9                               # max observed 0.80 SW + 0.1
    assert proposed["normalized_fps"][0] == 25.0 and proposed["sw_ratio"][0] == ts["sw_ratio"]
    assert proposed["finish_evidence_min_k"][0] == 3 and proposed["seeding_feasible"][0] == 4.25
    assert proposed["track_width_sl"][0] == 5.85 and proposed["axis_neighbourhood_k"][0] == 0
    reports = [json.loads(p.read_text()) for p in sorted((FIX / "pilot_reports").glob("*.json"))]
    pp, pw = propose_from_pilot(reports, ts)
    assert not pw and pp["dod3_median_target_min"][0] == 5 and pp["human_budget_cap_min"][0] == 8
    assert "raised to ceil(1.5 x target)" in pp["human_budget_cap_min"][1]
    # a sheet that fails its rule is NOT instantiated (prime directive)
    pp2, pw2 = propose_from_pilot([], ts)
    assert pp2 == {} and pw2


# --- binding and the freeze check -----------------------------------------------------------

def test_every_marker_in_the_committed_draft_binds_with_the_synthetic_registry():
    bs = [b for b in bind_markers(DRAFT, TEMPLATE, PASS_GATES) if b.kind != "header"]
    assert len(bs) == 20 and all(b.ok for b in bs), [b.problems for b in bs if not b.ok]
    kinds = {b.kind for b in bs}
    assert kinds == {"registry", "kill_gate", "kill_gates_all", "meta"}
    two_key = [b for b in bs if len(b.keys) == 2]
    assert all(len(b.nums) == 2 for b in two_key) and len(two_key) == 2          # the two §7.1 anchor rows
    four = [b for b in bs if len(b.keys) == 4 and b.kind == "registry"]
    assert len(four) == 1 and four[0].nums == [] and four[0].replacement == "frozen"  # EC-12


def test_real_registry_binds_all_markers_after_delegated_decisions():
    bs = [b for b in bind_markers(DRAFT, REAL_REGISTRY, REAL_GATES) if b.kind != "header"]
    assert all(b.ok for b in bs), [b.problems for b in bs if not b.ok]
    assert not load_default().thresholds["stratum_yield_review_factor"].eg


def test_freeze_check_blocks_on_registry_gates_markers_and_open_decisions():
    rep = check_freeze(REAL_REGISTRY, REAL_GATES, DRAFT, "DRAFT")
    assert not rep.allowed
    assert any(p.startswith("EG not instantiated") for p in rep.problems)
    assert any(p.startswith("kill-gate KG-1") for p in rep.problems)
    assert not any("binds to no registry entry" in p or "owner decision open" in p for p in rep.problems)
    assert rep.advisories and "KG-5" in rep.advisories[0]
    # fully instantiated synthetic registry + passing gates + stripped [OPEN] markers -> allowed
    ok = check_freeze(synthetic_registry(), PASS_GATES, strip_open_markers(DRAFT), "DRAFT")
    assert ok.allowed and ok.n_markers == 20 == ok.n_bound
    # New unbound markers still block promotion; settled decisions do not disable this guard.
    unbound = check_freeze(synthetic_registry(), PASS_GATES, DRAFT + '\n`unknown_key` 1 `[EG]`\n', "DRAFT")
    assert not unbound.allowed and any("binds to no registry entry" in p for p in unbound.problems)
    # FROZEN status with leftovers is flagged as inconsistent
    bad = check_freeze(REAL_REGISTRY, REAL_GATES, DRAFT, "FROZEN")
    assert bad.problems[0].startswith("SPEC_STATUS is FROZEN but markers remain")


# --- promotion refusals -----------------------------------------------------------------------

def test_refuses_on_uninstantiated_registry():
    with pytest.raises(PromotionRefused) as ei:
        promote(inputs(REAL_REGISTRY, REAL_GATES, strip_open=True))
    assert any("EG not instantiated" in r for r in ei.value.reasons)


def test_refuses_on_remaining_open_markers():
    inp = inputs(synthetic_registry(), PASS_GATES, strip_open=False)
    inp.draft_text += '\n`[OPEN: injected unresolved decision]`\n'
    with pytest.raises(PromotionRefused) as ei:
        promote(inp)
    assert all("owner decision open" in r for r in ei.value.reasons) and len(ei.value.reasons) == 1


def test_refuses_when_a_kill_gate_does_not_pass_or_the_spec_disagrees_with_the_registry():
    gates = json.loads(json.dumps(PASS_GATES))
    gates["gates"][1]["status"] = "recalibrate_once"
    with pytest.raises(PromotionRefused) as ei:
        promote(inputs(synthetic_registry(), gates))
    assert any("KG-2" in r for r in ei.value.reasons)
    reg = synthetic_registry()
    next(e for e in reg["entries"] if e["key"] == "cover_lat_sw")["provisional"] = 0.7   # spec says 0.8
    with pytest.raises(PromotionRefused) as ei2:
        promote(inputs(reg, PASS_GATES))
    assert any("spec writes 0.8 for cover_lat_sw but the registry provisional is 0.7" in r for r in ei2.value.reasons)


# --- the dry run itself -----------------------------------------------------------------------

def test_dry_run_produces_a_clean_frozen_spec_ts_log_and_version(tmp_path):
    reg = synthetic_registry()
    out = promote(inputs(reg, PASS_GATES))
    spec = out.frozen_spec
    assert "`[EG" not in spec and "`[OPEN" not in spec
    assert spec.startswith("# SPEC-2.0.0 — ") and spec.count("**Status:** FROZEN (normative)") == 1
    assert "**Freeze record (D-36):**" in spec and "**Promotion rule" not in spec
    lines = spec.splitlines()
    d25 = next(i for i, ln in enumerate(lines) if ln.startswith("| D-25 |"))
    assert [ln.split("|")[1].strip() for ln in lines[d25 + 1: d25 + 12]] == list(PENDING_IDS)
    assert lines[d25 + 13].startswith("**Appended at freeze (D-36):**")
    assert "(default **0.9 SW**)" in spec and "| `cover_lat_sw` | 0.9 |" in spec
    assert "| `anchor_offset_volte_s` / `anchor_offset_autostart_s` | 1.2 / 0.3 |" in spec
    assert "all four keys frozen)" in spec and "values frozen (`registers/kill_gates.yaml`)" in spec
    assert "Instantiating every evidence-gated value" in spec
    assert spec.rstrip().endswith("*End of SPEC-2.0.0.*")
    row = out.changelog_row
    assert row.startswith("| 2.0.0 | 2026-11-04 | FROZEN") and "`cover_lat_sw` 0.9 (provisional was 0.8)" in row
    assert spec.count(row) == 1 and spec.index("| 2.0.0-draft |") < spec.index(row) < spec.index("| 1.2.0 |")
    # lint_spec passes on the simulated frozen file (table hygiene, decision refs, no markers in a FROZEN spec)
    p = tmp_path / "SPEC-2.0.0.md"
    p.write_text(spec, encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools/lint_spec.py"), str(p), str(FIX / "evidence_gated.template.yaml")],
                       capture_output=True, text=True, cwd=ROOT, check=False)
    assert r.returncode == 0, r.stdout
    # frozen threshold set: loads, no eg keys, provenance "freeze", values = registry values
    tsp = tmp_path / "TS-2.0.0-frozen.yaml"
    tsp.write_text(out.frozen_ts, encoding="utf-8")
    fts = ThresholdSet.load(tsp)
    assert fts.version == "TS-2.0.0-frozen" and fts.spec_version == "2.0.0" and fts.calibrated is False
    assert fts.search_provenance == "freeze" and fts.evidence_gated_keys() == []
    assert set(fts.thresholds) == set(load_default().thresholds)
    for e in reg["entries"]:
        if e["key"] in fts.thresholds:
            assert float(fts[e["key"]]) == float(e["value"]), e["key"]
    assert fts["cover_lat_sw"] == 0.9 and fts["anchor_offset_volte_s"] == 1.2
    # decision log and version.py
    assert "## Closed (SPEC-2.0.0 §1) — D-26…D-36" in out.decision_log and "## Pending\n\nNone — the 2.0.0 line is frozen" in out.decision_log
    assert out.decision_log.count("| D-36 |") == 1
    assert 'SPEC_VERSION = "2.0.0"' in out.version_py and 'SPEC_STATUS = "FROZEN"' in out.version_py
    # and the repository's own version is untouched by all of this
    assert 'SPEC_STATUS = "DRAFT"' in VERSION_PY and not (ROOT / "spec" / "SPEC-2.0.0.md").exists()


def test_dry_run_is_deterministic():
    reg = synthetic_registry()
    a, b = promote(inputs(reg, PASS_GATES)), promote(inputs(reg, PASS_GATES))
    assert (a.frozen_spec, a.frozen_ts, a.decision_log, a.version_py) == (b.frozen_spec, b.frozen_ts, b.decision_log, b.version_py)


# --- CLI: dry run, guards, and the real run on an isolated copy -------------------------------

def test_cli_dry_run_writes_outputs_and_real_run_refuses_now(tmp_path):
    reg_path = tmp_path / "eg.yaml"
    reg_path.write_text(yaml.safe_dump(synthetic_registry(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    out_dir = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "tools/promote_draft.py"), "--dry-run", "--registry", str(reg_path),
                        "--kill-gates", str(FIX / "kill_gates_pass.yaml"), "--strip-open-markers", "--out-dir", str(out_dir),
                        "--date", "2026-11-04"], capture_output=True, text=True, cwd=ROOT, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert {p.name for p in out_dir.iterdir()} >= {"SPEC-2.0.0.md", "SPEC-2.0.0.md.diff", "TS-2.0.0-frozen.yaml", "DECISION-LOG.md",
                                                   "version.py", "promotion-report.md"}
    assert "DRY RUN OK" in r.stdout and "lint-spec: OK" in r.stdout
    # the real run refuses today (registry un-instantiated), and dry-run options are refused outside --dry-run
    real = subprocess.run([sys.executable, str(ROOT / "tools/promote_draft.py")], capture_output=True, text=True, cwd=ROOT, check=False)
    assert real.returncode == 1 and "REFUSED (promotion)" in real.stdout and "EG not instantiated" in real.stdout
    guard = subprocess.run([sys.executable, str(ROOT / "tools/promote_draft.py"), "--registry", str(reg_path)],
                           capture_output=True, text=True, cwd=ROOT, check=False)
    assert guard.returncode == 2 and "dry-run options" in guard.stdout
    assert not (ROOT / "spec" / "SPEC-2.0.0.md").exists() and not (ROOT / "config/thresholds/TS-2.0.0-frozen.yaml").exists()


def test_real_run_on_an_isolated_copy_is_idempotent_and_consistent(tmp_path):
    """Full rehearsal: copy the repository, drop the synthetic registry + passing gates in, resolve the [OPEN]
    markers as the owner would, promote for real, then promote again."""
    copy = tmp_path / "repo"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.egg-info", ".ruff_cache", "data"))
    (copy / "spec/registers/evidence_gated.yaml").write_text(yaml.safe_dump(synthetic_registry(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    shutil.copy(FIX / "kill_gates_pass.yaml", copy / "spec/registers/kill_gates.yaml")
    draft = copy / "spec/SPEC-2.0.0-draft.md"
    draft.write_text(strip_open_markers(draft.read_text(encoding="utf-8")), encoding="utf-8")
    tool = copy / "tools/promote_draft.py"
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1", "PATH": "/usr/bin:/bin"}
    first = subprocess.run([sys.executable, str(tool), "--date", "2026-11-04"], capture_output=True, text=True, cwd=copy, env=env, check=False)
    assert first.returncode == 0, first.stdout + first.stderr
    assert "PROMOTED" in first.stdout and (copy / "spec/SPEC-2.0.0.md").exists() and (copy / "config/thresholds/TS-2.0.0-frozen.yaml").exists()
    vpy = (copy / "src/tripstate/version.py").read_text()
    assert 'SPEC_VERSION = "2.0.0"' in vpy and 'SPEC_STATUS = "FROZEN"' in vpy
    assert "## Pending\n\nNone" in (copy / "spec/decisions/DECISION-LOG.md").read_text()
    second = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True, cwd=copy, env=env, check=False)
    assert second.returncode == 0 and "already frozen" in second.stdout
    assert (copy / "spec/SPEC-2.0.0.md").read_text() == (copy / "spec/SPEC-2.0.0.md").read_text()
    # the freeze check in the promoted copy is consistent (FROZEN, nothing remaining)
    fc = subprocess.run([sys.executable, str(copy / "tools/freeze_check.py")], capture_output=True, text=True, cwd=copy, env=env, check=False)
    assert fc.returncode == 0 and "FREEZE ALLOWED" in fc.stdout, fc.stdout
    # the frozen set becomes the default threshold set in the promoted copy
    code = ("import sys; sys.path.insert(0, 'src'); from tripstate.config import load_default; "
            "t = load_default(); print(t.version, t.spec_version, t.evidence_gated_keys())")
    probe = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=copy, env=env, check=False)
    assert probe.stdout.strip() == "TS-2.0.0-frozen 2.0.0 []", probe.stdout + probe.stderr
    # and the real repository is still DRAFT
    assert 'SPEC_STATUS = "DRAFT"' in (ROOT / "src/tripstate/version.py").read_text()
