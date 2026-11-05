"""Pilot stack on synthetic video: decode, detect, track, assign, seeded propagation, report, kill gates."""
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from tripstate.m4_geometry import ShotCalibration
from tripstate.m5_states import chart_race
from tripstate.pilot import FrameSource, render_synth_video, run_pilot_race
from tripstate.pilot.assign import SeedPoint, assign_seeds_to_tracks, identity_timeline
from tripstate.pilot.detect import BlobDetector, Detection, OracleDetector
from tripstate.pilot.frames import truth_boxes_from_json
from tripstate.pilot.report import aggregate, evaluate_kill_gates, markdown, write_kill_gates
from tripstate.pilot.track import IoUTracker, OraclePropagator
from tripstate.pilot.trackeval import hungarian_max, id_switches, idf1
from tripstate.synth import scripted_race, truth_frames

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    race = scripted_race(duration_s=6.0)
    out = tmp_path_factory.mktemp("pilot") / "synth.mp4"
    truth = render_synth_video(race, out, size=(640, 360))
    return race, out, truth


def seeds_from_truth(truth_boxes, frame, saddles):
    return [SeedPoint(frame, s, (b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2) for s, b in truth_boxes[frame].items() if s in saddles]


def truth_timeline(truth_boxes):
    return {f: {s: Detection(b.x1, b.y1, b.x2, b.y2, 1.0) for s, b in d.items()} for f, d in truth_boxes.items()}


def test_frame_source_decodes_rendered_video(synth):
    race, out, truth = synth
    src = FrameSource(out)
    frames = src.frame_cache()
    assert src.fps == 25.0 and len(frames) == len(race.frames()) and frames[0].shape == (360, 640, 3)
    assert Path(str(out) + ".truth.json").exists() and len(truth["boxes"]) == len(frames)


def test_blob_detector_components_and_filters():
    img = np.full((120, 200, 3), 20, np.uint8)
    img[10:30, 10:40] = 200          # box A
    img[50:70, 100:140] = 220        # box B
    img[90:92, 0:200] = 200          # thin line -> filtered by aspect
    img[100:102, 150:152] = 255      # speck -> filtered by area
    dets = BlobDetector().detect(0, img)
    assert [(d.x1, d.y1, d.x2, d.y2) for d in dets] == [(10.0, 10.0, 40.0, 30.0), (100.0, 50.0, 140.0, 70.0)]


def test_blob_detector_sees_runners_in_decoded_frame(synth):
    _race, out, _truth = synth
    frame = FrameSource(out).frame_cache()[0]
    dets = BlobDetector(min_area=30).detect(0, frame)
    assert 3 <= len(dets) <= 7     # touching/overlapping runner boxes merge; a real detector separates them


def test_hungarian_and_idf1_basics():
    m = np.array([[1, 5, 0], [4, 1, 0], [0, 0, 3]])
    pairs = sorted(hungarian_max(m))
    assert pairs == [(0, 1), (1, 0), (2, 2)]
    tl = {f: {1: Detection(0, 0, 10, 10, 1), 2: Detection(50, 0, 60, 10, 1)} for f in range(10)}
    assert idf1(tl, tl)["idf1"] == 1.0 and id_switches(tl, tl) == 0
    swapped = {f: (tl[f] if f < 5 else {2: tl[f][1], 1: tl[f][2]}) for f in range(10)}
    r = idf1(swapped, tl)
    assert 0.4 < r["idf1"] < 0.6 and id_switches(swapped, tl) == 2


def test_detector_path_tracks_and_assigns(synth, ts):
    race, _out, truth = synth
    tb = truth_boxes_from_json(truth)
    n = len(race.frames()); fps = race.fps
    det = OracleDetector(tb, jitter_px=0.3, dropout=0.02, seed=1)
    tracker = IoUTracker(ts, fps)
    for f in range(n):
        tracker.update(f, det.detect(f))
    saddles = truth["saddles"]
    seeds = seeds_from_truth(tb, 5, saddles)
    assignment, flags = assign_seeds_to_tracks(tracker.tracks, seeds)
    assert len(assignment) == len(saddles) and not flags
    tl = identity_timeline(tracker.tracks, assignment, n)
    m = idf1(tl, truth_timeline(tb))
    assert m["idf1"] > 0.85, m
    assert id_switches(tl, truth_timeline(tb)) <= 6


def test_seeded_path_flags_and_chart(synth, ts):
    race, _out, truth = synth
    tb = truth_boxes_from_json(truth)
    n = len(race.frames()); fps = race.fps; saddles = truth["saddles"]
    seeds = seeds_from_truth(tb, 5, saddles)
    rail = {int(k): tuple(v) for k, v in truth["rail"].items()}
    prop = OraclePropagator(tb, loss_windows={4: [(60, 80)], 6: [(90, 140)]})   # 0.8 s (coasted) and 2.0 s (> occl_max_s)
    tg, tt = truth_frames(race)
    truth_chart = chart_race(tg, tt, [(race.t0, race.tend)], race.t0, race.tend, ts)
    rep = run_pilot_race("SYN", n, fps, saddles, seeds, ShotCalibration(+1, "right_of_travel", True), ts, path="seeded",
                         propagator=prop, rail=rail, tend_s=race.tend, truth_timeline=truth_timeline(tb), truth_chart=truth_chart,
                         human_minutes=3.5, seeding_seconds_initial=95.0, official_elapsed_norm_s=race.tend, start_type="autostart")
    kinds = {(f["kind"], f["saddle_no"]) for f in rep.flags}
    assert ("lost", 4) in kinds and ("lost", 6) in kinds
    assert not any(f["frame"] < 5 for f in rep.flags)                  # nothing flagged before the prompts
    assert rep.chartable and rep.failure_codes == [] and rep.anchor["anchor_check_status"] == "pass"
    assert rep.tracker["idf1"] > 0.9 and rep.chart_vs_truth["uncovered_outside_iou"] > 0.85
    nv = {r["saddle_no"] for r in rep.segments if r["state"] == "NOT_VISIBLE" and r["t_start_frac"] > 0.1}   # after the pre-seed prefix
    assert 6 in nv and 4 not in nv                                      # EC-08: 0.8 s coasted (LOW_CONF), 2.0 s -> NOT_VISIBLE
    assert any(r["state"] == "LOW_CONF" and r["saddle_no"] == 4 for r in rep.segments)
    assert rep.producer_kind == "pilot_throwaway"
    assert len(rep.id_assignments) == len(seeds) and {r["seed_box_ref"] for r in rep.id_assignments} == {f"mask:{s.saddle_no}@5" for s in seeds}   # RP-18


def test_detector_path_report_with_tier_labels(synth, ts, tmp_path):
    race, _out, truth = synth
    tb = truth_boxes_from_json(truth)
    n = len(race.frames()); fps = race.fps; saddles = truth["saddles"]
    tg, _ = truth_frames(race)
    labels = [{"frame": f, "saddle_no": s, "tier_human": tg[s][f].tier} for f in range(0, n, 10) for s in saddles if tg[s][f].detected]
    rep = run_pilot_race("SYN", n, fps, saddles, seeds_from_truth(tb, 5, saddles), ShotCalibration(+1, "right_of_travel", True), ts,
                         path="detector", detector=OracleDetector(tb, seed=2), rail={int(k): tuple(v) for k, v in truth["rail"].items()},
                         tend_s=race.tend, tier_labels=labels, human_minutes=4.0)
    assert rep.tier_agreement is not None and rep.tier_agreement > 0.9 and rep.tier_agreement_n > 50
    assert len(rep.id_assignments) == len(saddles) and all(r["seed_box_ref"].startswith("track:") and r["seed_frame"] == 5 for r in rep.id_assignments)   # RP-18
    p = rep.write(tmp_path)
    assert json.loads(p.read_text())["path"] == "detector" and json.loads(p.read_text())["id_assignments"][0]["seed_x_px"] > 0


def test_aggregate_and_kill_gates(tmp_path):
    reports = [{"path": "seeded", "seeding_seconds_initial": 200, "tier_agreement": 0.9, "tier_agreement_n": 100, "chartable": True,
                "human_minutes": 4.0, "tracker": {"idf1": 0.95, "idsw": 1}, "flags": [{}] * 3},
               {"path": "seeded", "seeding_seconds_initial": 400, "tier_agreement": 0.8, "tier_agreement_n": 100, "chartable": False,
                "human_minutes": 9.0, "tracker": {"idf1": 0.9, "idsw": 2}, "flags": [{}] * 5}]
    agg = aggregate(reports, anchor_residuals={"volte": [1.0, 1.5, 2.0], "autostart": [0.2, 0.1]}, provisional_tol={"volte": 2.0, "autostart": 2.0})
    assert agg["KG-1"]["measured"] == 5.0 and agg["KG-2"]["measured"] == 0.85 and agg["KG-3"]["measured"] == 0.5
    st = evaluate_kill_gates(agg)
    assert st == {"KG-1": "pass", "KG-2": "pass", "KG-3": "pass", "KG-4": "pass"}
    repo_before = (ROOT / "spec/registers/kill_gates.yaml").read_text()
    kg = tmp_path / "kill_gates.yaml"
    kg.write_text(repo_before)
    write_kill_gates(kg, agg, "unit test")
    txt = kg.read_text()
    assert "status: pass" in txt and "status: not_evaluated" in txt   # KG-5 untouched
    assert (ROOT / "spec/registers/kill_gates.yaml").read_text() == repo_before   # repo file untouched
    md = markdown(agg, st)
    assert "KG-3 | 0.5" in md
    # A caller-supplied registry must control every numeric cutoff, including write-back.
    import yaml
    custom = yaml.safe_load(repo_before)
    for gate in custom["gates"]:
        if gate["id"] == "KG-1":
            gate["threshold_min"] = 4.0
        elif gate["id"] in ("KG-2", "KG-3"):
            gate["threshold"] = 0.95
        elif gate["id"] == "KG-4":
            gate["threshold_factor"] = 0.1
    assert evaluate_kill_gates(agg, custom) == {
        "KG-1": "fail", "KG-2": "recalibrate_once", "KG-3": "fail", "KG-4": "fail",
    }
    kg.write_text(yaml.safe_dump(custom), encoding="utf-8")
    assert write_kill_gates(kg, agg, "custom gate regression")["KG-1"] == "fail"
