"""RP-18 (L-51) — seed click provenance on id_assignments: DDL, writers, additive migration, canonical export, coexistence."""
import re
import sqlite3
from pathlib import Path

import pytest

from tripstate.m3_track import box_ref, id_assignment_rows, rows_from_pilot, rows_from_session
from tripstate.m8_storage import Store
from tripstate.m8_storage.store import DDL_PATH
from tripstate.pilot.assign import SeedPoint, assign_seeds_to_tracks
from tripstate.pilot.detect import Detection
from tripstate.pilot.track import Track
from tripstate.seeding.session import Seed

ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "spec" / "SPEC-2.0.0-draft.md").read_text(encoding="utf-8")


def race_row(rid):
    return {"race_id": rid, "date": "2026-11-03", "meeting": "R1", "race_no": 4, "base_distance_m": 2100, "start_type": "autostart",
            "start_format": "autostart", "start_handicap": False, "piste": "GP", "metadata_conflict_codes": []}


def test_spec_and_ddl_carry_the_three_columns():
    assert "`seed_x_px`, `seed_y_px`, `seed_box_ref`" in SPEC and "never a state coordinate" in SPEC
    st = Store()
    cols = st.columns("id_assignments")
    assert cols.index("seed_x_px") < cols.index("seed_y_px") < cols.index("seed_box_ref") < cols.index("extractor_version")


def test_rows_from_session_and_pilot_paths():
    seeds = [Seed(10, 0.4, 3, 100.0, 200.0), Seed(10, 0.4, 5, 300.0, 210.0), Seed(400, 16.0, 3, 120.0, 190.0, "human_correction")]
    rows = rows_from_session("R1", 1, {"fps": 25.0, "seeds": [s.__dict__ for s in seeds]})
    assert [(r["saddle_no"], r["method"], r["tracklet_id"], r["seed_box_ref"]) for r in rows] == [
        (3, "human_seed", 3, "mask:3@10"), (5, "human_seed", 5, "mask:5@10"), (3, "human_correction", 3, "mask:3@400")]
    assert rows[0]["seed_x_px"] == 100.0 and rows[0]["seed_y_px"] == 200.0 and rows[0]["seed_video_s"] == 0.4 and rows[0]["seed_frame"] == 10
    # pilot comparison path: the click lands on a tracklet box; a miss gives a flag, not a row
    tracks = {7: Track(7, {10: Detection(90, 150, 130, 230, 0.9), 11: Detection(91, 150, 131, 230, 0.9)})}
    assignment, flags = assign_seeds_to_tracks(tracks, [SeedPoint(10, 3, 100.0, 200.0), SeedPoint(10, 5, 900.0, 900.0)])
    assert assignment == {7: 3} and [f["kind"] for f in flags] == ["seed_missed"]
    prow = rows_from_pilot("R1", 1, [{"frame": 10, "saddle_no": 3, "x": 100.0, "y": 200.0}, {"frame": 10, "saddle_no": 5, "x": 900.0, "y": 900.0}],
                           assignment, tracks, fps=25.0)
    assert len(prow) == 1 and prow[0]["tracklet_id"] == 7 and prow[0]["seed_box_ref"] == box_ref("track", 7, 10) == "track:7@10"
    assert prow[0]["seed_video_s"] == 0.4
    assert id_assignment_rows("R1", 1, seeds, lambda s: None) == []


def test_rows_persist_export_canonically_and_coexist_across_producers():
    seeds = [Seed(10, 0.4, 3, 100.0, 200.0), Seed(12, 0.48, 5, 300.5, 210.25)]
    rows = rows_from_session("R1", 1, {"fps": 25.0, "seeds": [s.__dict__ for s in seeds]})
    a, b = Store(), Store()
    for st, created in ((a, "t1"), (b, "t2")):
        st.insert("races", [race_row("R1")], producer_version="pv1", created_at=created)
        st.insert("id_assignments", rows, producer_version="pv1", created_at=created, extractor_version="e1", threshold_set_version="T1")
    canon = a.canonical("id_assignments")
    assert '"seed_x_px":"100.000000"' in canon and '"seed_box_ref":"mask:3@10"' in canon and '"seed_y_px":"210.250000"' in canon   # pixels: default 6 dp (L-39)
    assert a.canonical_sha("id_assignments") == b.canonical_sha("id_assignments")
    # a second producer (a re-seeding session) coexists under its own key and changes only its own canonical payload
    a.insert("id_assignments", [dict(r, seed_x_px=r["seed_x_px"] + 1.0) for r in rows], producer_version="pv2", created_at="t3",
             extractor_version="e1", threshold_set_version="T1")
    assert len(a.rows("id_assignments")) == 4
    assert a.canonical_sha("id_assignments", "pv1") == b.canonical_sha("id_assignments", "pv1")
    assert a.canonical_sha("id_assignments") != b.canonical_sha("id_assignments")
    back = a.rows("id_assignments", {"producer_version": "pv1"})
    assert back[0]["human_confirmed"] is True and back[0]["seed_box_ref"] == "mask:3@10"


def test_additive_migration_adds_the_columns_to_an_older_store(tmp_path):
    old_ddl = re.sub(r"\n  seed_x_px REAL, seed_y_px REAL, seed_box_ref TEXT,[^\n]*", "", DDL_PATH.read_text(encoding="utf-8"))
    assert "seed_x_px" not in old_ddl
    db = tmp_path / "old.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(old_ddl)
    conn.execute("INSERT INTO races (race_id, date, meeting, race_no, base_distance_m, start_type, start_format, start_handicap, schema_version, producer_version, created_at) "
                 "VALUES ('R1','d','m',1,2100,'autostart','autostart',0,'2.0.0-draft','pv','t')")
    conn.execute("INSERT INTO id_assignments (race_id, shot_id, tracklet_id, saddle_no, method, human_confirmed, extractor_version, threshold_set_version, "
                 "schema_version, producer_version, created_at) VALUES ('R1',1,7,3,'human_seed',1,'e','T','2.0.0-draft','pv','t')")
    conn.commit(); conn.close()
    st = Store(db)                       # apply_schema() runs the additive migration
    assert {"seed_x_px", "seed_y_px", "seed_box_ref"} <= set(st.columns("id_assignments"))
    old_row = st.rows("id_assignments")[0]
    assert old_row["seed_x_px"] is None and old_row["seed_box_ref"] is None     # absent provenance stays NULL, never invented
    assert st.migrate_additive() == []                                           # idempotent
    st.insert("id_assignments", rows_from_session("R1", 1, {"fps": 25.0, "seeds": [Seed(10, 0.4, 4, 1.0, 2.0).__dict__]}),
              producer_version="pv2", created_at="t", extractor_version="e", threshold_set_version="T")
    assert '"seed_box_ref":"mask:4@10"' in st.canonical("id_assignments", "pv2")


def test_breaking_changes_are_refused_by_the_additive_migration(tmp_path, monkeypatch):
    db = tmp_path / "s.sqlite"
    Store(db).conn.close()
    ddl = DDL_PATH.read_text(encoding="utf-8").replace("  seed_x_px REAL,", "  seed_x_px REAL, mandatory_new TEXT NOT NULL,")
    fake = tmp_path / "ddl.sql"
    fake.write_text(ddl, encoding="utf-8")
    monkeypatch.setattr("tripstate.m8_storage.store.DDL_PATH", fake)
    with pytest.raises(RuntimeError, match="breaking change"):
        Store(db)
