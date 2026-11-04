"""C8 — frame JSON + store + manifest → calibration inputs; round-trip into the §7.2 harness."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

from tripstate.calibration import DevRace, RaceGeometry, grid_search
from tripstate.calibration.search import candidate_ts
from tripstate.m4_geometry import ShotCalibration, ShotProjector, frames_from_json, frames_to_json
from tripstate.m8_storage import Store
from tripstate.release.synthetic_store import build_synthetic_store
from tripstate.synth import render_boxes, scripted_race

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from export_calibration_inputs import export  # noqa: E402 -- import the repository tool after bootstrapping its directory


def test_frames_json_round_trips_every_runner_field(ts):
    race = scripted_race(duration_s=2.0)
    saddles = [r.saddle_no for r in race.runners]
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    rendered = render_boxes(race)
    frames = [proj.project(t, boxes, rail, 0.9, saddles) for t, boxes, rail in rendered]
    heights = {t: {b.saddle_no: b.y2 - b.y1 for b in boxes} for t, boxes, _ in rendered}
    text = frames_to_json(frames, "R", race.t0, race.tend, [(race.t0, race.tend)], saddles, box_heights=heights)
    back, meta = frames_from_json(text)
    assert meta["race_id"] == "R" and meta["saddles"] == saddles and meta["intervals"] == [(race.t0, race.tend)]
    assert [f.t for f in back] == [f.t for f in frames] and back[20].axis_method == frames[20].axis_method
    assert [r.__dict__ for r in back[20].runners] == [r.__dict__ for r in frames[20].runners]
    assert meta["box_heights"][frames[20].t][1] == 48.0
    assert frames_to_json(back, "R", race.t0, race.tend, [(race.t0, race.tend)], saddles, box_heights=meta["box_heights"]) == text


def test_export_round_trips_into_the_calibration_harness(ts, tmp_path):
    frames_dir, out = tmp_path / "frames", tmp_path / "cal"
    store, manifest = build_synthetic_store(ts, n_heldout=2, n_dev=2, n_breaks=2, frames_dir=frames_dir)
    done, problems = export(frames_dir, store, manifest, out, split="dev")
    assert problems == [] and len(done) == 2
    races = []
    for rid in done:
        geom = RaceGeometry.from_json((out / f"{rid}.geometry.json").read_text())
        rows = json.loads((out / f"{rid}.hand_chart.json").read_text())
        assert geom.race_id == rid and all(r["split"] == "dev" and r["method"] == "human_chart" for r in rows)
        assert geom.frames[10].runners[1].box_h_px == 48.0 and geom.producer.startswith("synthetic-extractor")
        races.append(DevRace(rid, geom, rows, "dev"))
    # the sidecars carry box heights, so the uncalibrated M6 reference detector also runs and its load constraint
    # applies: on the scripted race (crossings, a detachment) it overshoots the §7.2 cap, which the harness reports
    # rather than hides. Relax only that cap to show the geometry recovery through the exported inputs.
    # (The scripted race's lanes sit exactly 1 SW apart, so cover_lat_sw is not discriminable on it; same_tier_sw is:
    # at 1.2 SW the lanes merge and the tiers collapse.)
    space = {"same_tier_sw": [0.6, 1.2]}
    strict = grid_search(candidate_ts(ts, {"same_tier_sw": 1.2}), space, races)
    assert strict.best is None and all(any("candidate load" in v for v in r.violations) for r in strict.results)
    relaxed = dict(strict.constraints, candidate_load_median_max=1e9)
    res = grid_search(candidate_ts(ts, {"same_tier_sw": 1.2}), space, races, constraints=relaxed)
    assert res.best is not None and res.best.overrides == {"same_tier_sw": 0.6} and res.best.headline > 0.95
    assert min(r.headline for r in res.results) < 0.9


def test_export_refuses_bad_inputs_all_or_nothing(ts, tmp_path):
    frames_dir, out = tmp_path / "frames", tmp_path / "cal"
    store, manifest = build_synthetic_store(ts, n_heldout=2, n_dev=2, n_breaks=2, frames_dir=frames_dir)
    rid = next(e["race_id"] for e in manifest["entries"] if e["split"] == "dev")
    # split mismatch (S-6)
    store.conn.execute("UPDATE hand_charts SET split = 'heldout' WHERE race_id = ?", (rid,))
    done, problems = export(frames_dir, store, manifest, out, split="dev")
    assert done == [] and any("S-6" in p and rid in p for p in problems) and not out.exists()
    store.conn.execute("UPDATE hand_charts SET split = 'dev' WHERE race_id = ?", (rid,))
    # ambiguous human producer -> refuse, then select one
    extra = [dict(r, producer_version="charter-2") for r in store.rows("hand_charts", {"race_id": rid})]
    for r in extra:
        r.pop("schema_version"); r.pop("created_at")
    store.insert("hand_charts", extra, producer_version="charter-2", created_at="x")
    done, problems = export(frames_dir, store, manifest, out, split="dev")
    assert done == [] and any("human producers" in p for p in problems)
    done, problems = export(frames_dir, store, manifest, out, split="dev", human_producer="charter-2")
    assert done == [] and any("no hand chart from producer 'charter-2'" in p for p in problems)   # the other dev race lacks it
    done, problems = export(frames_dir, store, manifest, out, races=[rid], human_producer="charter-2")
    assert problems == [] and done == [rid]
    # missing frames file / unknown race / wrong race_id inside the file
    (frames_dir / f"{rid}.frames.json").rename(frames_dir / "moved.json")
    done, problems = export(frames_dir, store, manifest, tmp_path / "cal2", split="dev", human_producer="charter-2")
    assert done == [] and any("missing" in p for p in problems)
    (frames_dir / "moved.json").rename(frames_dir / f"{rid}.frames.json")
    done, problems = export(frames_dir, store, manifest, tmp_path / "cal2", races=["NOPE"], human_producer="charter-2")
    assert done == [] and problems == ["NOPE: not in the golden manifest"]
    doc = json.loads((frames_dir / f"{rid}.frames.json").read_text()); doc["race_id"] = "OTHER"
    (frames_dir / f"{rid}.frames.json").write_text(json.dumps(doc))
    done, problems = export(frames_dir, store, manifest, tmp_path / "cal2", races=[rid], human_producer="charter-2")
    assert done == [] and any("carries race_id 'OTHER'" in p for p in problems)


def test_cli_exports_and_calibrate_still_refuses_while_draft(ts, tmp_path):
    frames_dir, out, db = tmp_path / "frames", tmp_path / "cal", tmp_path / "s.sqlite"
    store, manifest = build_synthetic_store(ts, n_heldout=2, n_dev=2, n_breaks=2, frames_dir=frames_dir, path=str(db))
    store.conn.close()
    mp = tmp_path / "manifest.yaml"
    mp.write_text(yaml.safe_dump(manifest, sort_keys=False))
    r = subprocess.run([sys.executable, str(ROOT / "tools/export_calibration_inputs.py"), "--frames-dir", str(frames_dir), "--store", str(db),
                        "--manifest", str(mp), "--out", str(out), "--split", "all"], capture_output=True, text=True, check=False)
    assert r.returncode == 0 and "exported 4 races" in r.stdout, r.stdout + r.stderr
    assert len(list(out.glob("*.geometry.json"))) == 4
    cal = subprocess.run([sys.executable, str(ROOT / "tools/calibrate.py"), "--ts", str(ROOT / "config/thresholds/TS-0.0.0-provisional.yaml"),
                          "--space", str(ROOT / "config/calibration/search-space.yaml"), "--dev-dir", str(out), "--manifest", str(mp),
                          "--version", "TS-x", "--out", str(tmp_path / "x.yaml")], capture_output=True, text=True, check=False)
    assert cal.returncode == 1 and "D-36" in cal.stdout
    Store(db).conn.close()
