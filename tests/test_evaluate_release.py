"""B6 — DoD-1…6 release evaluation on a synthetic store (SPEC-2.0.0-draft §0.2, §6.3; D-31, D-35)."""
import subprocess
import sys
from pathlib import Path

import pytest

from tripstate.release.evaluate import changelog_row, evaluate_release, render_markdown
from tripstate.release.synthetic_store import build_synthetic_store

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("damage", ["missing_chart", "wrong_split"])
def test_incomplete_or_unsealed_heldout_truth_cannot_pass_accuracy(ts, damage):
    store, manifest = build_synthetic_store(ts)
    rid = next(e["race_id"] for e in manifest["entries"] if e["split"] == "heldout")
    if damage == "missing_chart":
        store.conn.execute("DELETE FROM hand_charts WHERE race_id = ?", (rid,))
    else:
        store.conn.execute("UPDATE hand_charts SET split = 'dev' WHERE race_id = ?", (rid,))
    ev = evaluate_release(store, manifest, ts, "x", "2026-11-04")
    assert ev.dod("DoD-6").status == "pass"
    for id_ in ("DoD-1", "DoD-2"):
        assert ev.dod(id_).status == "invalid"
        assert rid in ev.dod(id_).summary


def test_selected_producer_does_not_borrow_break_candidates_from_another_run(ts):
    store, manifest = build_synthetic_store(ts)
    candidates = [r for r in store.rows("events") if r["method"] == "cv_extract"]
    for row in candidates:
        row["producer_version"] = "other-cv-run"
    store.insert("events", candidates, producer_version="other-cv-run", created_at="2026-11-04T00:00:00")
    store.conn.execute("DELETE FROM events WHERE method = 'cv_extract' AND producer_version = 'synth-cv-0.1'")
    ev = evaluate_release(store, manifest, ts, "x", "2026-11-04", producer_version="synth-cv-0.1")
    assert ev.dod("DoD-2").details["matched"] == 0
    assert ev.dod("DoD-2").status == "fail"


def test_full_synthetic_store_passes_every_dod_and_renders_every_line(ts):
    st1, manifest = build_synthetic_store(ts, created_at="2026-11-04T00:00:00")
    st2, _ = build_synthetic_store(ts, created_at="2026-11-04T01:00:00")
    ev = evaluate_release(st1, manifest, ts, "synthetic", "2026-11-04", store2=st2)
    assert [d.id for d in ev.dods] == [f"DoD-{i}" for i in range(1, 7)]
    assert ev.complete and all(d.status == "pass" for d in ev.dods), [(d.id, d.status, d.summary) for d in ev.dods]
    d2 = ev.dod("DoD-2").details
    assert d2["matched"] == 8 and d2["n_observable_truth_breaks"] == 10 and 0.48 < d2["wilson_95"][0] < 0.50
    assert ev.dod("DoD-3").details["n_attempts"] == 22 and ev.dod("DoD-3").details["n_over_budget"] == 1
    assert ev.dod("DoD-6").details["n_pass_q1_q6"] == 9          # one held-out race fails Q-1 (void), one is over_budget only
    assert ev.headline_with_q7["n_races"] == 9 and ev.headline_without_q7["n_races"] == 8   # D-35 dual report
    assert ev.headline_with_q7["headline"] > 0.95 and ev.headline_without_q7["headline"] > 0.95
    assert ev.dod("DoD-5").details["canonical_identity"] is True
    assert ev.strata_yield["review_trigger"] == [] and len(ev.strata_yield["per_stratum"]) == 6
    md = render_markdown(ev)
    for needle in ("| DoD-1 | **pass**", "| DoD-6 | **pass**", "with Q-7 failures", "without Q-7 failures",
                   "## Per-stratum yield", "## Per-stratum headline", "## Changelog row draft", "v1 Definition of Done: COMPLETE"):
        assert needle in md, needle
    row = changelog_row(ev)
    assert row.startswith("| 2.0.0-draft | 2026-11-04 | Release evaluation synthetic") and row.count("|") == 4 and "v1 complete" in row
    assert any("golden manifest does not validate" in n for n in ev.notes)   # a 22-race synthetic manifest is not a §6.1 manifest


def test_undersized_fixtures_give_the_right_invalidity_reasons(ts):
    st, manifest = build_synthetic_store(ts, n_heldout=6, n_dev=2, n_breaks=4)
    ev = evaluate_release(st, manifest, ts, "small", "2026-11-04")
    assert not ev.complete
    d6, d1, d2, d3, d5 = (ev.dod(i) for i in ("DoD-6", "DoD-1", "DoD-2", "DoD-3", "DoD-5"))
    assert d6.status == "invalid" and "6 races in the manifest" in d6.summary and "requires 10" in d6.summary
    assert d1.status == "invalid" and "because DoD-6 is invalid" in d1.summary
    assert d2.status == "invalid" and "because DoD-6 is invalid" in d2.summary
    assert d3.status == "invalid" and "8 eligible attempts" in d3.summary and "(< 20)" in d3.summary
    assert d5.status == "not_evaluated" and "--store2" in d5.summary
    # enough held-out races but too few observable breaks: DoD-2 invalid on its own count
    st, manifest = build_synthetic_store(ts, n_heldout=10, n_dev=12, n_breaks=6)
    ev = evaluate_release(st, manifest, ts, "fewbreaks", "2026-11-04")
    assert ev.dod("DoD-6").status == "pass" and ev.dod("DoD-1").status == "pass"
    assert ev.dod("DoD-2").status == "invalid" and "observable held-out BREAK starts (< 10)" in ev.dod("DoD-2").summary


def test_dod5_detects_a_differing_second_run_and_dod2_fails_below_the_floor(ts):
    a, manifest = build_synthetic_store(ts, recall_misses=2)
    b, _ = build_synthetic_store(ts, recall_misses=4)          # different candidate set -> different canonical events
    ev = evaluate_release(a, manifest, ts, "x", "2026-11-04", store2=b)
    assert ev.dod("DoD-5").status == "fail" and "events" in ev.dod("DoD-5").details["tables_differing"]
    ev_b = evaluate_release(b, manifest, ts, "y", "2026-11-04")
    assert ev_b.dod("DoD-2").status == "fail" and ev_b.dod("DoD-2").details["matched"] < 8


def test_cli_synthetic_writes_report_and_real_mode_needs_arguments(tmp_path):
    out = tmp_path / "rel"
    r = subprocess.run([sys.executable, str(ROOT / "tools/evaluate_release.py"), "--synthetic", "--out-dir", str(out), "--date", "2026-11-04"],
                       capture_output=True, text=True, cwd=ROOT, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (out / "evaluation.md").exists() and (out / "evaluation.json").exists() and (out / "changelog-row.md").exists()
    assert "SYNTHETIC store — not evidence" in r.stdout
    r2 = subprocess.run([sys.executable, str(ROOT / "tools/evaluate_release.py"), "--store", "x.sqlite"], capture_output=True, text=True, cwd=ROOT, check=False)
    assert r2.returncode == 2 and "missing --manifest" in r2.stdout
