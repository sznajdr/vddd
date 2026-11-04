"""A4 — calibration harness (§7.2) on synthetic races. Code only: the real run is refused while DRAFT (D-36)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tripstate.calibration import RaceGeometry, grid_search, load_search_space, rederive
from tripstate.calibration.holdout import changelog_row, evaluate_heldout
from tripstate.calibration.search import candidate_ts, evaluate_candidate
from tripstate.calibration.synthetic import (
    RACE_A,
    SYNTHETIC_SPACE,
    hand_chart_from,
    static_geometry,
    synthetic_races,
)
from tripstate.calibration.tsio import provenance, write_threshold_set
from tripstate.config import ThresholdSet
from tripstate.m4_geometry import ShotCalibration, ShotProjector, to_frame_geoms
from tripstate.synth import render_boxes, scripted_race

ROOT = Path(__file__).resolve().parents[1]


def test_sidecar_round_trips_and_rederives_the_projector_tiers(ts):
    """Stored M4 geometry + rederive(ts) == what ShotProjector emitted (tiers, ranks), so calibration re-runs
    exactly the pack-space step it is allowed to, and nothing upstream."""
    race = scripted_race(duration_s=4.0)
    saddles = [r.saddle_no for r in race.runners]
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    rendered = render_boxes(race)
    frames = [proj.project(t, boxes, rail, 0.9, saddles) for t, boxes, rail in rendered]
    heights = {t: {b.saddle_no: b.y2 - b.y1 for b in boxes} for t, boxes, _ in rendered}
    geom = RaceGeometry.from_projector("S", frames, saddles, race.t0, race.tend, [(race.t0, race.tend)], heights)
    back = RaceGeometry.from_json(geom.to_json())
    assert back.to_json() == geom.to_json() and back.sha256() == geom.sha256() and back.frames[10].runners[4].box_h_px == 48.0
    direct, times = to_frame_geoms(frames, saddles)
    re_frames, re_times, ranks = rederive(back, ts)
    assert re_times == times
    for s in saddles:
        assert [f.tier for f in re_frames[s]] == [f.tier for f in direct[s]], s
        assert [f.detected for f in re_frames[s]] == [f.detected for f in direct[s]]
    by = {r.saddle_no: r for r in frames[60].runners}
    assert ranks[1][60] == by[1].rank_long == 1 and ranks[7][60] == by[7].rank_long


def test_grid_search_recovers_perturbed_thresholds_within_one_step(ts):
    dev, _held = synthetic_races(ts)
    mis = candidate_ts(ts, {"cover_lat_sw": 0.5, "same_tier_sw": 0.4})
    before = evaluate_candidate(mis, {}, dev)
    assert not before.feasible and before.headline < 0.7
    res = grid_search(mis, SYNTHETIC_SPACE, dev)
    assert res.best is not None and res.best.overrides == {"cover_lat_sw": 0.8, "same_tier_sw": 0.6}
    assert abs(res.best.headline - 1.0) < 1e-9 and res.best.candidate_load_median == 0.0
    # the optimum is strict: every neighbour one grid step away scores lower
    by = {(r.overrides["cover_lat_sw"], r.overrides["same_tier_sw"]): r.headline for r in res.results}
    for nb in ((0.7, 0.6), (0.9, 0.6), (0.8, 0.5), (0.8, 0.7)):
        assert by[nb] < 1.0 - 1e-6, nb
    assert len(res.results) == 25 and res.reasons == []
    # determinism: same inputs, same ordering, same winner
    res2 = grid_search(mis, SYNTHETIC_SPACE, dev)
    assert [r.as_dict() for r in res2.results] == [r.as_dict() for r in res.results]


def test_search_rejects_heldout_races_and_reports_infeasible_grids(ts):
    dev, held = synthetic_races(ts)
    with pytest.raises(ValueError):
        grid_search(ts, SYNTHETIC_SPACE, dev + held)
    res = grid_search(ts, {"cover_lat_sw": [0.6], "same_tier_sw": [0.4]}, dev)
    assert res.best is None and "spec revision" in res.reasons[0]


def test_hand_chart_rows_carry_the_shared_payload(ts):
    g = static_geometry("X", RACE_A)
    rows = hand_chart_from(g, ts, "dev")
    assert rows and all(r["method"] == "human_chart" and r["split"] == "dev" and r["race_id"] == "X" for r in rows)
    states = {(r["saddle_no"], r["state"]) for r in rows if r["state_kind"] == "base"}
    assert {(1, "LEADER"), (2, "RAIL_UNCOVERED"), (3, "OUTSIDE_COVERED"), (4, "PARKED"), (5, "RAIL_COVERED"), (6, "WIDE")} == states


def test_tsio_provenance_round_trips_through_threshold_set_load(ts, tmp_path):
    out = tmp_path / "TS-9.9.yaml"
    prov = provenance(SYNTHETIC_SPACE, "headline_score", {"uncovered_outside_iou_floor": 0.85, "covered_iou_floor": 0.85,
                      "candidate_load_median_max": 4}, {"headline": 1.0, "uncovered_outside_iou": 1.0, "covered_iou": 1.0,
                      "rest_macro": 1.0, "candidate_load_median": 0.0, "n_candidates": 25}, ["A", "B"], "2026-11-04", ts.version, 1)
    write_threshold_set(ts.path, out, "TS-9.9", {"cover_lat_sw": 0.85, "same_tier_sw": 0.55}, prov)
    loaded = ThresholdSet.load(out)
    assert loaded.version == "TS-9.9" and loaded.calibrated is True
    assert loaded["cover_lat_sw"] == 0.85 and loaded["same_tier_sw"] == 0.55 and loaded["min_state_s"] == ts["min_state_s"]
    assert loaded.search_provenance["keys"] == {k: list(v) for k, v in SYNTHETIC_SPACE.items()}
    assert loaded.search_provenance["best_score"] == 1.0 and loaded.search_provenance["dev_races"] == ["A", "B"]
    assert set(loaded.thresholds) == set(ts.thresholds)
    with pytest.raises(KeyError):
        write_threshold_set(ts.path, tmp_path / "bad.yaml", "TS-9.9", {"no_such_key": 1}, prov)


def test_heldout_gap_rule_and_changelog_row(ts):
    dev, held = synthetic_races(ts)
    good = evaluate_heldout(ts, held, dev_headline=1.0)
    assert good.verdict == "accept" and good.gap_pt == 0.0
    wrong = evaluate_heldout(candidate_ts(ts, {"same_tier_sw": 0.4, "cover_lat_sw": 0.6}), held, dev_headline=1.0)
    assert wrong.verdict == "spec_revision" and wrong.gap_pt > 10 and "do not tune further" in wrong.notes[0]
    with pytest.raises(ValueError):
        evaluate_heldout(ts, dev, 1.0)
    assert evaluate_heldout(ts, [], 1.0).verdict == "not_evaluable"
    row = changelog_row("2.0.0", "2026-11-04", "TS-2.1.0", "ex", good)
    assert row.startswith("| 2.0.0 | 2026-11-04 | Held-out evaluation") and row.count("|") == 4 and "Verdict: accept" in row


def test_declared_search_space_is_valid_except_for_eg_keys_before_the_freeze(ts):
    sp = load_search_space(ROOT / "config/calibration/search-space.yaml")
    assert sp.method == "grid" and sp.n_candidates == 75
    assert sp.validate(ts, allow_eg=True) == []
    problems = sp.validate(ts)
    assert problems and all("evidence-gated" in p for p in problems)   # cover_lat_sw / same_tier_sw are [EG] until OD-1x


def test_cli_refuses_real_run_while_draft_and_runs_synthetic(tmp_path):
    real = subprocess.run([sys.executable, str(ROOT / "tools/calibrate.py"), "--ts", str(ROOT / "config/thresholds/TS-0.0.0-provisional.yaml"),
                           "--space", str(ROOT / "config/calibration/search-space.yaml"), "--dev-dir", str(tmp_path),
                           "--manifest", str(tmp_path / "missing.yaml"), "--version", "TS-x", "--out", str(tmp_path / "x.yaml")],
                          capture_output=True, text=True, cwd=ROOT, check=False)
    assert real.returncode == 1 and "REFUSED" in real.stdout and "D-36" in real.stdout
    syn = subprocess.run([sys.executable, str(ROOT / "tools/calibrate.py"), "--synthetic", "--out-dir", str(tmp_path / "syn"),
                          "--perturb", "cover_lat_sw=0.6", "--perturb", "same_tier_sw=0.8", "--date", "2026-11-04"],
                         capture_output=True, text=True, cwd=ROOT, check=False)
    assert syn.returncode == 0, syn.stdout + syn.stderr
    assert "SYNTHETIC DRY RUN OK" in syn.stdout and "-> accept" in syn.stdout
    search = json.loads((tmp_path / "syn" / "search.json").read_text())
    assert search["best"]["overrides"] == {"cover_lat_sw": 0.8, "same_tier_sw": 0.6}
    assert (tmp_path / "syn" / "TS-synthetic-calibrated.yaml").exists() and (tmp_path / "syn" / "changelog-row.md").exists()
