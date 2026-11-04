"""End-to-end on a synthetic race: render -> M4 -> M5 -> M7 -> M8, compared with the scripted truth."""
from tripstate.evaluation.metrics import (
    REST_STATES,
    edit_score,
    headline_score,
    is_covered,
    is_uncovered_outside,
    macro_iou,
    mask_iou,
    per_runner_state_iou,
)
from tripstate.m4_geometry import ShotCalibration, ShotProjector, to_frame_geoms
from tripstate.m5_states import chart_race
from tripstate.m7_qc import RaceQCInput, Shot, coverage_fractions, evaluate_gates, shot_gap_events
from tripstate.m8_storage import Store, ordinal_ids
from tripstate.synth import render_boxes, scripted_race, truth_frames


def run_pipeline(ts, race):
    saddles = [r.saddle_no for r in race.runners]
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    frames = [proj.project(t, boxes, rail, 0.9, saddles) for t, boxes, rail in render_boxes(race)]
    geoms, times = to_frame_geoms(frames, saddles)
    iv = [(race.t0, race.tend)]
    return chart_race(geoms, times, iv, race.t0, race.tend, ts), saddles


def test_pipeline_reproduces_scripted_truth(ts):
    race = scripted_race()
    pred, saddles = run_pipeline(ts, race)
    tg, tt = truth_frames(race)
    truth = chart_race(tg, tt, [(race.t0, race.tend)], race.t0, race.tend, ts)
    mask = [(0.0, 1.0)]
    uo = mask_iou(pred, truth, mask, is_uncovered_outside)
    cov = mask_iou(pred, truth, mask, is_covered)
    rest = macro_iou({s: per_runner_state_iou(pred, truth, mask, s) for s in REST_STATES})
    assert uo > 0.95 and cov > 0.95 and rest > 0.95, (uo, cov, rest)
    assert headline_score(uo, cov, rest) > 0.95
    for s in saddles:
        p = [r for r in pred if r["saddle_no"] == s]; t = [r for r in truth if r["saddle_no"] == s]
        assert edit_score(p, t) >= 80.0, (s, [r["state"] for r in p], [r["state"] for r in t])
    # scripted facts visible in the predicted chart
    st = {(r["saddle_no"], r["state"]) for r in pred if r["state_kind"] == "base"}
    assert (1, "LEADER") in st and (2, "POCKET") in st and (3, "RAIL_COVERED") in st
    assert (4, "PARKED") in st and (4, "OUTSIDE_COVERED") in st and (6, "WIDE") in st
    assert any(r["state"] == "DETACHED" and r["end_attr"] == "rear" and r["saddle_no"] == 7 for r in pred)
    assert any(r["state"] == "NOT_VISIBLE" and r["saddle_no"] == 5 for r in pred)
    leads = [r for r in pred if r["lead_uncovered_outside"] is True]
    assert {r["saddle_no"] for r in leads} == {4, 5}


def test_qc_and_store_on_synthetic_race(ts):
    race = scripted_race(duration_s=10.0)
    pred, saddles = run_pipeline(ts, race)
    shots = [Shot("wide_pan", race.t0, race.tend)]
    assert shot_gap_events(shots, race.t0, race.tend) == []
    cr, cf = coverage_fractions([(race.t0, race.tend)], race.t0, race.tend)
    g = evaluate_gates(RaceQCInput(cr, cf, True, False, False, 0.0, len(saddles), "attele", 3.0), ts)
    assert g.chartable
    store = Store()
    rows = ordinal_ids([dict(r, race_id="S1") for r in pred], "seg_id", "t_start_frac")
    store.insert("races", [{"race_id": "S1", "date": "d", "meeting": "m", "race_no": 1, "base_distance_m": 2100,
                            "start_type": "autostart", "start_format": "autostart", "start_handicap": False,
                            "metadata_conflict_codes": []}], producer_version="pv", created_at="a")
    store.insert("qc", [{"race_id": "S1", "chartable": True, "failure_codes": [], "id_suspect": False, "anchor_suspect": False}],
                 producer_version="pv", created_at="a", extractor_version="e", threshold_set_version=ts.version)
    store.insert("state_segments", rows, producer_version="pv", created_at="a", extractor_version="e", threshold_set_version=ts.version)
    sha1 = store.canonical_sha("state_segments")
    # DoD-5: a second run on the same inputs reproduces the canonical payload
    pred2, _ = run_pipeline(ts, race)
    store2 = Store()
    store2.insert("state_segments", ordinal_ids([dict(r, race_id="S1") for r in pred2], "seg_id", "t_start_frac"),
                  producer_version="pv", created_at="b", extractor_version="e", threshold_set_version=ts.version)
    assert store2.canonical_sha("state_segments") == sha1
    assert len(store.feature_export()) == len(rows)
