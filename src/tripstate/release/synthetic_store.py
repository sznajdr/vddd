"""Synthetic M8 store + golden manifest for the release-evaluation dry run (tools/evaluate_release.py --synthetic).

Builds N scripted races through M4→M5→M7 (the pipeline the synth-demo runs), writes CV rows (`state_segments`,
`events` candidates, `qc`, `runner_qc`, `race_anchors`) and human rows (`hand_charts` from the scripted truth,
`events` BREAK truths) into a Store, plus a manifest dict. Deterministic: the same arguments produce the same
canonical payload (DoD-5 is checked by building twice). NOT evidence for anything (§7)."""
from __future__ import annotations

from pathlib import Path

from tripstate.config import ThresholdSet
from tripstate.m4_geometry import ShotCalibration, ShotProjector, frames_to_json, to_frame_geoms
from tripstate.m5_states import chart_race
from tripstate.m7_qc import RaceQCInput, evaluate_gates, runner_qc_row
from tripstate.m8_storage import Store, ordinal_ids
from tripstate.synth import render_boxes, scripted_race, truth_frames

PRODUCER_CV, PRODUCER_HUMAN = "synth-cv-0.1", "synth-human-0.1"
EXTRACTOR, FORMATS, PISTES = "synthetic-extractor", ("autostart", "volte_flat", "volte_handicap"), ("GP", "PP")


def _race_rows(i: int, rid: str, fmt: str, piste: str, n_runners: int) -> tuple[dict, list[dict]]:
    base = 2100 if fmt == "autostart" else 2850
    race = {"race_id": rid, "date": f"2026-01-{1 + i % 28:02d}", "meeting": f"R{1 + i % 2}", "race_no": 1 + i % 8, "base_distance_m": base,
            "start_type": "autostart" if fmt == "autostart" else "volte", "start_format": fmt, "start_handicap": fmt == "volte_handicap",
            "piste": piste, "metadata_conflict_codes": []}
    runners = [{"race_id": rid, "saddle_no": s, "distance_run_m": base + (25 if fmt == "volte_handicap" and s > 4 else 0),
                "rendement_m": 25 if fmt == "volte_handicap" and s > 4 else 0, "time_normalization_status": "unavailable", "conflict_codes": []}
               for s in range(1, n_runners + 1)]
    return race, runners


def build_synthetic_store(ts: ThresholdSet, n_heldout: int = 10, n_dev: int = 12, n_breaks: int = 12, recall_misses: int = 2,
                          created_at: str = "2026-11-04T00:00:00", path: str = ":memory:", frames_dir: Path | None = None) -> tuple[Store, dict]:
    """frames_dir: when given, also writes <race_id>.frames.json (tripstate.m4.frames/1) per race — the C8 exporter input."""
    st = Store(path)
    if frames_dir is not None:
        Path(frames_dir).mkdir(parents=True, exist_ok=True)
    entries = []
    break_budget, miss_budget = n_breaks, recall_misses
    st.insert("versions", [{"producer_version": PRODUCER_CV, "producer_kind": "cv_extract", "extractor_version": EXTRACTOR},
                           {"producer_version": PRODUCER_HUMAN, "producer_kind": "human_chart"}], producer_version="x", created_at=created_at)
    for i in range(n_heldout + n_dev):
        split = "heldout" if i < n_heldout else "dev"
        rid = f"SYN-{split[:3].upper()}-{i:02d}"
        fmt, piste = FORMATS[i % 3], PISTES[i % 2]
        race = scripted_race(duration_s=6.0 + (i % 3))
        saddles = [r.saddle_no for r in race.runners]
        proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
        rendered = render_boxes(race)
        frames = [proj.project(t, boxes, rail, 0.9, saddles) for t, boxes, rail in rendered]
        geoms, times = to_frame_geoms(frames, saddles)
        iv = [(race.t0, race.tend)]
        if frames_dir is not None:
            heights = {t: {b.saddle_no: b.y2 - b.y1 for b in boxes} for t, boxes, _ in rendered}
            (Path(frames_dir) / f"{rid}.frames.json").write_text(
                frames_to_json(frames, rid, race.t0, race.tend, iv, saddles, producer=f"{EXTRACTOR}/{ts.version}", box_heights=heights),
                encoding="utf-8")
        pred = chart_race(geoms, times, iv, race.t0, race.tend, ts)
        tg, tt = truth_frames(race)
        truth = chart_race(tg, tt, iv, race.t0, race.tend, ts)
        race_row, runner_rows = _race_rows(i, rid, fmt, piste, len(saddles))
        st.insert("races", [race_row], producer_version=PRODUCER_CV, created_at=created_at)
        st.insert("runners", runner_rows, producer_version=PRODUCER_CV, created_at=created_at)
        st.insert("race_anchors", [{"race_id": rid, "t0_video_s": race.t0, "tend_video_s": race.tend, "official_time_method": "unavailable",
                                    "anchor_check_status": "inconclusive", "anchor_suspect": False, "human_confirmed": True}],
                  producer_version=PRODUCER_CV, created_at=created_at, extractor_version=EXTRACTOR, threshold_set_version=ts.version)
        # QC: most races chartable; one held-out race over budget (Q-7 only), one failing Q-1 (void for accuracy)
        minutes = 3.0 + (i % 5) * 0.7 + (9.5 - 3.0) * (i == 1)
        cov = 0.5 if i == 2 else 0.9
        g = evaluate_gates(RaceQCInput(cov, 0.9, True, False, False, 0.0, len(saddles), "attele", minutes), ts)
        st.insert("qc", [{"race_id": rid, "chartable": g.chartable, "failure_codes": g.failure_codes, "coverage_race": cov, "coverage_final_third": 0.9,
                          "human_minutes": minutes, "stratum": "night" if i % 2 else "day", "id_suspect": False, "anchor_suspect": False}],
                  producer_version=PRODUCER_CV, created_at=created_at, extractor_version=EXTRACTOR, threshold_set_version=ts.version)
        st.insert("state_segments", ordinal_ids([dict(r, race_id=rid) for r in pred], "seg_id", "t_start_frac"),
                  producer_version=PRODUCER_CV, created_at=created_at, extractor_version=EXTRACTOR, threshold_set_version=ts.version)
        st.insert("runner_qc", [runner_qc_row(rid, s, [r for r in pred if r["saddle_no"] == s]) for s in saddles],
                  producer_version=PRODUCER_CV, created_at=created_at, extractor_version=EXTRACTOR, threshold_set_version=ts.version)
        hc = [dict(r, race_id=rid, method="human_chart", confidence=None, charter_minutes=12.0, split=split) for r in truth]
        st.insert("hand_charts", ordinal_ids(hc, "seg_id", "t_start_frac"), producer_version=PRODUCER_HUMAN, created_at=created_at)
        # breaks: held-out truths (observable, runner 2 at 0.45) until the budget is spent; candidates for all but `recall_misses`
        ev_h, ev_c = [], []
        if split == "heldout" and break_budget > 0:
            per = min(2, break_budget)
            for k in range(per):
                s, f = 2 + k, 0.45 + 0.2 * k
                ev_h.append({"race_id": rid, "saddle_no": s, "type": "BREAK", "t_start_frac": f, "t_end_frac": f + 0.05, "recovered": True,
                             "method": "human_chart", "review_status": "accepted", "human_confirmed": True})
                if miss_budget > 0 and k == 0:          # the first truth of each held-out race goes uncaught until the budget is spent
                    miss_budget -= 1
                else:
                    ev_c.append({"race_id": rid, "saddle_no": s, "type": "BREAK", "t_start_frac": f + 0.01, "t_end_frac": None,
                                 "method": "cv_extract", "review_status": "pending", "human_confirmed": False})
            break_budget -= per
        ev_c.append({"race_id": rid, "saddle_no": 6, "type": "BREAK", "t_start_frac": 0.8, "t_end_frac": None, "method": "cv_extract",
                     "review_status": "rejected", "human_confirmed": False})   # a false candidate per race (load)
        if ev_h:
            st.insert("events", ordinal_ids(ev_h, "event_id", "t_start_frac"), producer_version=PRODUCER_HUMAN, created_at=created_at)
        st.insert("events", ordinal_ids(ev_c, "event_id", "t_start_frac"), producer_version=PRODUCER_CV, created_at=created_at,
                  extractor_version=EXTRACTOR, threshold_set_version=ts.version)
        entries.append({"race_id": rid, "date": race_row["date"], "start_format": fmt, "piste": piste, "day_night": "night" if i % 2 else "day",
                        "field_size": len(saddles), "boring": i % 4 == 0, "expected_breaks": 2 if split == "heldout" else 1,
                        "source_hash": f"synthetic-{i}", "distance_band": None, "excluded_from_heldout": False, "split": split})
    manifest = {"manifest_version": "synthetic", "created_at": created_at, "seed": 0, "attempt": 0, "reason": "synthetic dry run",
                "n_dev": n_dev, "n_heldout": n_heldout, "strata_summary": {}, "entries": sorted(entries, key=lambda e: e["race_id"]), "replacements": []}
    return st, manifest
