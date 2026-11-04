#!/usr/bin/env python3
"""Run one pilot race (protocols/PILOT-5) on a video with the chosen backends and write report_<path>.json.

  pilot_run.py --video V --race ID --out DIR --path seeded   --propagator oracle|sam2 [--sam2-ckpt ...] [--truth T.json]
  pilot_run.py --video V --race ID --out DIR --path detector --detector oracle|blob|gdino|owlv2|yolo [--truth T.json]
Seeds come from --session (seed_cli output) or --seeds (JSON list). --truth enables the oracle backends and
IDF1/ID-switch/chart metrics against the synthetic truth; on real replays the "truth" is the operator-corrected result.
Race metadata (fps, anchors, calibration) comes from --race-json (synth_video.py writes one) or flags.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.config import ThresholdSet, default_threshold_path
from tripstate.m4_geometry import ShotCalibration
from tripstate.m5_states import chart_race
from tripstate.pilot.assign import SeedPoint
from tripstate.pilot.detect import BlobDetector, Detection, OracleDetector
from tripstate.pilot.frames import FrameSource, truth_boxes_from_json
from tripstate.pilot.run import run_pilot_race
from tripstate.pilot.track import OraclePropagator


def load_seeds(a) -> list[SeedPoint]:
    if a.session:
        sess = json.loads(Path(a.session).read_text())
        return [SeedPoint(s["frame"], s["saddle_no"], s["x"], s["y"]) for s in sess["seeds"]]
    return [SeedPoint(s["frame"], s["saddle_no"], s["x"], s["y"]) for s in json.loads(Path(a.seeds).read_text())]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True); ap.add_argument("--race", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--path", required=True, choices=["seeded", "detector"])
    ap.add_argument("--session"); ap.add_argument("--seeds"); ap.add_argument("--race-json"); ap.add_argument("--truth"); ap.add_argument("--tier-labels")
    ap.add_argument("--detector", default="blob", choices=["oracle", "blob", "gdino", "owlv2", "yolo"])
    ap.add_argument("--propagator", default="oracle", choices=["oracle", "sam2", "session"]); ap.add_argument("--sam2-ckpt"); ap.add_argument("--sam2-cfg", default="configs/sam2.1/sam2.1_hiera_s.yaml")
    ap.add_argument("--ts", default=str(default_threshold_path()))
    ap.add_argument("--travel-sign", type=int); ap.add_argument("--rail-side"); ap.add_argument("--t0", type=float); ap.add_argument("--tend", type=float)
    ap.add_argument("--human-minutes", type=float, help="dry runs only: stand-in operator minutes when the session is headless")
    ap.add_argument("--official-elapsed", type=float); ap.add_argument("--start-type", default="autostart"); ap.add_argument("--field-size", type=int)
    a = ap.parse_args()
    ts = ThresholdSet.load(a.ts)
    meta = json.loads(Path(a.race_json).read_text()) if a.race_json else {}
    sess = json.loads(Path(a.session).read_text()) if a.session else {}
    src = FrameSource(Path(a.video))
    fps, n = src.fps, src.n_frames
    travel = a.travel_sign or (sess.get("orientation") or {}).get("travel_direction_sign") or meta.get("travel_sign", 1)
    rail_side = a.rail_side or (sess.get("orientation") or {}).get("rail_side") or meta.get("rail_side", "right_of_travel")
    anchors = sess.get("anchors") or {}
    t0 = a.t0 if a.t0 is not None else (anchors.get("t0_video_s") if anchors.get("t0_video_s") is not None else meta.get("t0_s", 0.0))
    tend = a.tend if a.tend is not None else (anchors.get("tend_video_s") if anchors.get("tend_video_s") is not None else meta.get("tend_s", (n - 1) / fps))
    seeds = load_seeds(a)
    saddles = meta.get("saddles") or sorted({s.saddle_no for s in seeds})

    truth = json.loads(Path(a.truth).read_text()) if a.truth else None
    tb = truth_boxes_from_json(truth) if truth else None
    rail = {int(k): tuple(v) for k, v in truth["rail"].items()} if truth else None
    truth_tl = {f: {s: Detection(b.x1, b.y1, b.x2, b.y2, 1.0) for s, b in d.items()} for f, d in tb.items()} if tb else None
    truth_chart = None
    if truth and meta.get("race_id") == "SYNTH-1":
        from tripstate.synth import scripted_race, truth_frames
        race = scripted_race(duration_s=meta["tend_s"] - meta["t0_s"])
        tg, tt = truth_frames(race)
        truth_chart = chart_race(tg, tt, [(race.t0, race.tend)], race.t0, race.tend, ts)
    labels = None
    if a.tier_labels:
        with open(a.tier_labels, newline="") as f:
            labels = [{"frame": int(r["frame"]), "saddle_no": int(r["saddle_no"]), "tier_human": int(r["tier_human"])} for r in csv.DictReader(f)]

    kw = {}
    if a.path == "detector":
        if a.detector == "oracle":
            if tb is None:
                raise SystemExit("--detector oracle needs --truth")
            kw["detector"] = OracleDetector(tb, jitter_px=0.3, dropout=0.02)
        elif a.detector == "blob":
            kw["detector"] = BlobDetector(); kw["frames_iter"] = iter(src)
        elif a.detector == "gdino":
            from tripstate.pilot.detect import GroundingDinoDetector
            kw["detector"] = GroundingDinoDetector(); kw["frames_iter"] = iter(src)
        elif a.detector == "owlv2":
            from tripstate.pilot.detect import OWLv2Detector
            kw["detector"] = OWLv2Detector(); kw["frames_iter"] = iter(src)
        else:
            from tripstate.pilot.detect import UltralyticsDetector
            kw["detector"] = UltralyticsDetector(travel_sign=travel); kw["frames_iter"] = iter(src)
    else:
        if a.propagator == "oracle":
            if tb is None:
                raise SystemExit("--propagator oracle needs --truth")
            kw["propagator"] = OraclePropagator(tb)
        elif a.propagator == "session":
            from tripstate.seeding import SessionTimelinePropagator
            if not sess.get("timeline"):
                raise SystemExit("--propagator session needs a session recorded with a live engine (seed_cli --engine ...)")
            kw["propagator"] = SessionTimelinePropagator(sess)
        else:
            from tripstate.pilot.track import SAM2Propagator
            kw["propagator"] = SAM2Propagator(str(a.video), a.sam2_ckpt, a.sam2_cfg)

    rep = run_pilot_race(a.race, n, fps, saddles, seeds, ShotCalibration(travel, rail_side, True), ts, path=a.path,
                         rail=rail, t0_s=t0, tend_s=tend, official_elapsed_norm_s=a.official_elapsed if a.official_elapsed is not None else meta.get("official_elapsed_norm_s"),
                         start_type=a.start_type, truth_timeline=truth_tl, truth_chart=truth_chart, tier_labels=labels,
                         human_minutes=a.human_minutes if a.human_minutes is not None else (None if sess.get("headless") else sess.get("human_minutes")),
                         seeding_seconds_initial=None if sess.get("headless") else sess.get("seeding_seconds_initial"),
                         field_size=a.field_size, **kw)
    p = rep.write(Path(a.out))
    print(json.dumps({"report": str(p), "chartable": rep.chartable, "failure_codes": rep.failure_codes, "flags": len(rep.flags),
                      "tracker": rep.tracker, "tier_agreement": rep.tier_agreement, "chart_vs_truth": rep.chart_vs_truth,
                      "human_minutes": rep.human_minutes}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
