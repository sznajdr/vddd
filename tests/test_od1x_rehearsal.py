"""C6 — the OD-1x rehearsal target and the scriptable stopwatch (rehearsal rows only)."""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "od1x_synthetic"


def test_scripted_timer_writes_a_rehearsal_row_and_refuses_real_race_ids(tmp_path):
    answers = {"video_timecode_s": 10.0, "wait_s": 0.05, "n_assigned": 7, "n_unassigned": 0, "n_wrong_after_check": 0, "id_cues": "cloth", "notes": "x"}
    (tmp_path / "a.json").write_text(json.dumps(answers))
    sheet = tmp_path / "sheet_seeding.csv"
    r = subprocess.run([sys.executable, str(ROOT / "tools/od1x_timer.py"), "--race", "SYNTH-T", "--attempt", "2", "--sheet", str(sheet),
                        "--script", str(tmp_path / "a.json")], capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    rows = list(csv.DictReader(sheet.open(encoding="utf-8")))
    assert rows[0]["frame_kind"] == "mid_race_reseed" and rows[0]["notes"].startswith("REHEARSAL") and float(rows[0]["seconds_elapsed"]) >= 0.0
    bad = subprocess.run([sys.executable, str(ROOT / "tools/od1x_timer.py"), "--race", "20261103-R1-C4", "--sheet", str(sheet),
                          "--script", str(tmp_path / "a.json")], capture_output=True, text=True, check=False)
    assert bad.returncode == 2 and "REFUSED" in bad.stdout and len(list(csv.DictReader(sheet.open(encoding="utf-8")))) == 1


def test_rehearsal_matches_the_committed_fixture_expectations(tmp_path):
    out = tmp_path / "rehearsal"
    args = [sys.executable, str(ROOT / "tools/od1x_rehearsal.py"), "--out", str(out), "--duration", "4"]
    if shutil.which("ffmpeg") is None:
        args.append("--skip-video")
    r = subprocess.run(args, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "REHEARSAL OK" in r.stdout and "matches tests/fixtures/od1x_synthetic/expected_proposals.json" in r.stdout
    assert {p.name for p in (out / "od1x").glob("*.csv")} == {p.name for p in (ROOT / "protocols/OD-1x/sheets").glob("*.csv")}
    got = json.loads((out / "fixture_proposals.json").read_text())
    exp = json.loads((FIX / "expected_proposals.json").read_text())
    assert {k: v["value"] for k, v in got.items()} == exp
    if shutil.which("ffmpeg"):
        assert (out / "synth" / "synth.mp4").exists() and (out / "synth" / "race.json").exists()
