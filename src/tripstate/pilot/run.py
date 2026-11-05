"""Run one pilot race on either identity path, produce a report (protocols/PILOT-5 measurements)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from tripstate.config import ThresholdSet
from tripstate.evaluation.metrics import (
    REST_STATES,
    edit_score,
    is_covered,
    is_uncovered_outside,
    macro_iou,
    mask_iou,
    per_runner_state_iou,
)
from tripstate.m3_track.assignments import id_assignment_rows, rows_from_pilot
from tripstate.m3_track.checks import anchor_check
from tripstate.m4_geometry import Box, ShotCalibration, ShotProjector, to_frame_geoms
from tripstate.m5_states import chart_race
from tripstate.m7_qc import RaceQCInput, coverage_fractions, evaluate_gates
from tripstate.pilot.assign import (
    SeedPoint,
    assign_seeds_to_tracks,
    coast_gaps,
    identity_timeline,
    propagation_flags,
    reseed_flags,
)
from tripstate.pilot.detect import Detection, Detector
from tripstate.pilot.track import IoUTracker, SeededPropagator
from tripstate.pilot.trackeval import id_switches, idf1, mota_lite

PRODUCER_KIND = "pilot_throwaway"


@dataclass
class PilotRaceReport:
    race_id: str
    path: str                                   # 'seeded' | 'detector'
    producer_kind: str = PRODUCER_KIND
    n_frames: int = 0
    seeds: int = 0
    flags: list[dict] = field(default_factory=list)
    tracker: dict = field(default_factory=dict)  # idf1 / idsw / mota vs corrected truth (if supplied)
    tier_agreement: float | None = None
    tier_agreement_n: int = 0
    coverage_race: float | None = None
    coverage_final_third: float | None = None
    chartable: bool | None = None
    failure_codes: list[str] = field(default_factory=list)
    anchor: dict = field(default_factory=dict)
    human_minutes: float | None = None
    seeding_seconds_initial: float | None = None
    chart_vs_truth: dict = field(default_factory=dict)
    segments: list[dict] = field(default_factory=list)
    id_assignments: list[dict] = field(default_factory=list)   # RP-18 rows (seed click provenance); shot_id 0 = the pilot's single charted interval set

    def write(self, out_dir: Path) -> Path:
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / f"report_{self.path}.json"
        p.write_text(json.dumps(asdict(self), indent=1), encoding="utf-8")
        return p


def _boxes_to_m4(frame_boxes: dict[int, dict[int, Detection]], saddles: list[int], n_frames: int, fps: float,
                 calibration: ShotCalibration, rail: dict[int, tuple[float, float]] | None, rail_conf: float, ts: ThresholdSet):
    proj = ShotProjector(ts, calibration, fps)
    frames = []
    for f in range(n_frames):
        boxes = [Box(s, d.x1, d.y1, d.x2, d.y2, d.conf) for s, d in sorted(frame_boxes.get(f, {}).items())]
        rp = tuple(rail[f]) if rail and f in rail else None
        frames.append(proj.project(f / fps, boxes, rp, rail_conf if rp else None, saddles))
    return frames


def tier_agreement(frames, labels: list[dict]) -> tuple[float | None, int]:
    """labels: [{frame, saddle_no, tier_human}] against M4 absolute tiers; `frames` is indexed by frame (KG-2).
    Frames where M4 is unresolved (tier None) count as disagreements: an abstention is not agreement."""
    ok = n = 0
    for lab in labels:
        f = int(lab["frame"])
        if f < 0 or f >= len(frames):
            continue
        r = next((r for r in frames[f].runners if r.saddle_no == lab["saddle_no"]), None)
        if r is None or not r.detected:
            continue
        n += 1
        ok += int(r.tier == lab["tier_human"])
    return (ok / n if n else None), n


def run_pilot_race(
    race_id: str,
    n_frames: int,
    fps: float,
    saddles: list[int],
    seeds: list[SeedPoint],
    calibration: ShotCalibration,
    ts: ThresholdSet,
    *,
    path: str,
    detector: Detector | None = None,
    frames_iter=None,
    propagator: SeededPropagator | None = None,
    rail: dict[int, tuple[float, float]] | None = None,
    rail_conf: float = 0.9,
    intervals: list[tuple[float, float]] | None = None,
    t0_s: float = 0.0,
    tend_s: float | None = None,
    official_elapsed_norm_s: float | None = None,
    start_type: str = "autostart",
    truth_timeline: dict[int, dict[int, Detection]] | None = None,
    truth_chart: list[dict] | None = None,
    tier_labels: list[dict] | None = None,
    human_minutes: float | None = None,
    seeding_seconds_initial: float | None = None,
    field_size: int | None = None,
) -> PilotRaceReport:
    rep = PilotRaceReport(race_id, path, n_frames=n_frames, seeds=len(seeds), human_minutes=human_minutes,
                          seeding_seconds_initial=seeding_seconds_initial)
    tend_s = tend_s if tend_s is not None else (n_frames - 1) / fps
    intervals = intervals or [(t0_s, tend_s)]
    max_gap = round(float(ts["occl_max_s"]) * fps)   # EC-08: coast this long, then NOT_VISIBLE

    if path == "detector":
        assert detector is not None
        tracker = IoUTracker(ts, fps)
        frame_src = frames_iter if frames_iter is not None else ((f, f / fps, None) for f in range(n_frames))
        for f, _, img in frame_src:
            tracker.update(f, detector.detect(f, img))
        assignment, aflags = assign_seeds_to_tracks(tracker.tracks, seeds)
        timeline = identity_timeline(tracker.tracks, assignment, n_frames, max_gap)
        rep.id_assignments = rows_from_pilot(race_id, 0, seeds, assignment, tracker.tracks, fps)
        rep.flags = sorted(aflags + reseed_flags(tracker.tracks, assignment, saddles, n_frames, fps), key=lambda x: (x["frame"], x["kind"]))
    elif path == "seeded":
        assert propagator is not None
        for s in seeds:
            propagator.add_prompt(s.frame, s.saddle_no, s.x, s.y)
        prop = propagator.run()
        per_id: dict[int, dict[int, Detection]] = {}
        for f, objs in prop.items():
            for o, (b, _) in objs.items():
                per_id.setdefault(o, {})[f] = b
        timeline = {f: {} for f in range(n_frames)}
        for o, boxes in per_id.items():
            for f, b in coast_gaps(boxes, max_gap).items():
                if f < n_frames:
                    timeline[f][o] = b
        prompt_frames: dict[int, int] = {}
        for sd in seeds:
            prompt_frames[sd.saddle_no] = min(prompt_frames.get(sd.saddle_no, sd.frame), sd.frame)
        rep.id_assignments = id_assignment_rows(race_id, 0, seeds, lambda s: int(s["saddle_no"]), fps, ref_kind="mask")
        rep.flags = propagation_flags(prop, sorted(prompt_frames), n_frames, float(ts["mask_conf_flag"]),
                                      float(ts["mask_overlap_flag"]), round(float(ts["overlap_flag_s"]) * fps), prompt_frames)
    else:
        raise ValueError(path)

    if truth_timeline is not None:
        rep.tracker = {**idf1(timeline, truth_timeline), "idsw": id_switches(timeline, truth_timeline), **mota_lite(timeline, truth_timeline)}

    frames = _boxes_to_m4(timeline, saddles, n_frames, fps, calibration, rail, rail_conf, ts)
    if tier_labels:
        rep.tier_agreement, rep.tier_agreement_n = tier_agreement(frames, tier_labels)
    geoms, times = to_frame_geoms(frames, saddles)
    rep.segments = chart_race(geoms, times, intervals, t0_s, tend_s, ts)

    coherent = [(f.t, f.t + 1 / fps) for f in frames if f.conf > 0 and sum(r.detected for r in f.runners) >= int(ts["pack_min_visible"])]
    rep.coverage_race, rep.coverage_final_third = coverage_fractions(coherent, t0_s, tend_s)
    rep.anchor = anchor_check(tend_s - t0_s, official_elapsed_norm_s, start_type, ts)
    g = evaluate_gates(RaceQCInput(rep.coverage_race, rep.coverage_final_third, True, bool(rep.anchor["anchor_suspect"]),
                                   any(f["kind"] == "id_conflict" for f in rep.flags), 0.0, field_size or len(saddles), "attele",
                                   human_minutes), ts)
    rep.chartable, rep.failure_codes = g.chartable, g.failure_codes

    if truth_chart is not None:
        mask = [(0.0, 1.0)]
        uo = mask_iou(rep.segments, truth_chart, mask, is_uncovered_outside)
        cov = mask_iou(rep.segments, truth_chart, mask, is_covered)
        rest = macro_iou({s: per_runner_state_iou(rep.segments, truth_chart, mask, s) for s in REST_STATES})
        rep.chart_vs_truth = {"uncovered_outside_iou": uo, "covered_iou": cov, "rest_macro": rest,
                              "edit_mean": float(np.mean([edit_score([r for r in rep.segments if r["saddle_no"] == s],
                                                                      [r for r in truth_chart if r["saddle_no"] == s]) for s in saddles]))}
    return rep
