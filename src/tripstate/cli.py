"""`tripstate` command line (thin; the human protocols stay in tools/).

  tripstate ingest-video SRC OUT_DIR [--fps 25]        M0 video normalization
  tripstate synth-demo [--out DIR]                       scripted synthetic race through M4→M5→M7→M8
  tripstate evaluate PRED.json TRUTH.json                §6.2 headline on two segment-row files
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _synth_demo(out: Path | None) -> int:
    from tripstate.config import load_default
    from tripstate.evaluation.metrics import edit_score, is_covered, is_uncovered_outside, mask_iou
    from tripstate.m4_geometry import ShotCalibration, ShotProjector, to_frame_geoms
    from tripstate.m5_states import chart_race
    from tripstate.m7_qc import RaceQCInput, evaluate_gates
    from tripstate.m8_storage import Store, ordinal_ids
    from tripstate.synth import render_boxes, scripted_race, truth_frames

    ts = load_default()
    race = scripted_race()
    saddles = [r.saddle_no for r in race.runners]
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    frames = [proj.project(t, boxes, rail, 0.9, saddles) for t, boxes, rail in render_boxes(race)]
    geoms, times = to_frame_geoms(frames, saddles)
    iv = [(race.t0, race.tend)]
    pred = chart_race(geoms, times, iv, race.t0, race.tend, ts)
    tg, tt = truth_frames(race)
    truth = chart_race(tg, tt, iv, race.t0, race.tend, ts)
    mask = [(0.0, 1.0)]
    report = {}
    for s in saddles:
        p = [r for r in pred if r["saddle_no"] == s]
        t = [r for r in truth if r["saddle_no"] == s]
        report[s] = {"uncovered_outside_iou": mask_iou(p, t, mask, is_uncovered_outside),
                     "covered_iou": mask_iou(p, t, mask, is_covered), "edit": edit_score(p, t)}
    gates = evaluate_gates(RaceQCInput(1.0, 1.0, True, False, False, 0.0, len(saddles), "attele", 4.0), ts)
    st = Store(out / "synth.sqlite" if out else ":memory:")
    rows = [dict(r, race_id="SYNTH-1") for r in pred]
    st.insert("races", [{"race_id": "SYNTH-1", "date": "2026-01-01", "meeting": "S", "race_no": 1, "base_distance_m": 2100,
                         "start_type": "autostart", "start_format": "autostart", "start_handicap": False, "piste": "GP",
                         "metadata_conflict_codes": []}], producer_version="synth", created_at="now")
    st.insert("qc", [{"race_id": "SYNTH-1", "chartable": gates.chartable, "failure_codes": gates.failure_codes,
                      "id_suspect": False, "anchor_suspect": False}], producer_version="synth", created_at="now",
              extractor_version="synth", threshold_set_version=ts.version)
    st.insert("state_segments", ordinal_ids(rows, "seg_id", "t_start_frac"), producer_version="synth", created_at="now",
              extractor_version="synth", threshold_set_version=ts.version)
    print(json.dumps({"per_runner": report, "gates": gates.__dict__, "segments": len(rows),
                      "canonical_sha_state_segments": st.canonical_sha("state_segments")}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tripstate", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    iv = sub.add_parser("ingest-video"); iv.add_argument("src"); iv.add_argument("out_dir"); iv.add_argument("--fps", type=float)
    sd = sub.add_parser("synth-demo"); sd.add_argument("--out")
    ev = sub.add_parser("evaluate"); ev.add_argument("pred"); ev.add_argument("truth")
    a = ap.parse_args(argv)
    if a.cmd == "ingest-video":
        from tripstate.config import load_default
        from tripstate.m0_ingest.video import normalize_video
        fps = a.fps or float(load_default()["normalized_fps"])
        r = normalize_video(Path(a.src), Path(a.out_dir), fps)
        print(json.dumps(r.__dict__, indent=1, default=str))
        return 1 if r.ingest_failed else 0
    if a.cmd == "synth-demo":
        out = Path(a.out) if a.out else None
        if out:
            out.mkdir(parents=True, exist_ok=True)
        return _synth_demo(out)
    if a.cmd == "evaluate":
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
        pred = json.loads(Path(a.pred).read_text()); truth = json.loads(Path(a.truth).read_text())
        mask = [(0.0, 1.0)]
        uo = mask_iou(pred, truth, mask, is_uncovered_outside); cov = mask_iou(pred, truth, mask, is_covered)
        rest = macro_iou({s: per_runner_state_iou(pred, truth, mask, s) for s in REST_STATES})
        print(json.dumps({"uncovered_outside_iou": uo, "covered_iou": cov, "rest_macro": rest,
                          "headline": headline_score(uo, cov, rest), "edit_score": edit_score(pred, truth)}, indent=1))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
