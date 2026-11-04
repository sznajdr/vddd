#!/usr/bin/env python3
"""OD-1x stopwatch for step 1 (timed seeding). Appends one row per attempt to sheet_seeding.csv.

Interactive (the owner's afternoon):
  od1x_timer.py --race 20261103-R1-C4 --attempt 1 --sheet data/od1x/sheet_seeding.csv
  Press Enter to start, Enter again to stop, then answer the prompts.

Scripted (rehearsal only, `make od1x-rehearsal`): the stopwatch still runs for real, but the answers come from a
JSON file and the row is marked REHEARSAL. Refuses a race_id that does not start with `SYNTH-` so a scripted row
can never land in a real sheet as evidence.
  od1x_timer.py --race SYNTH-REHEARSAL --attempt 1 --sheet /tmp/od1x/sheet_seeding.csv --script answers.json
  answers.json: {"video_timecode_s": 66.0, "wait_s": 0.2, "n_assigned": 7, "n_unassigned": 0,
                 "n_wrong_after_check": 0, "id_cues": "cloth", "notes": "..."}
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

FIELDS = ["race_id", "attempt", "frame_kind", "video_timecode_s", "seconds_elapsed",
          "n_assigned", "n_unassigned", "n_wrong_after_check", "id_cues", "notes"]
REHEARSAL_NOTE = "REHEARSAL (synthetic clip, scripted answers) — not evidence"


def frame_kind(attempt: int) -> str:
    return "first_stable_wide_pan" if attempt == 1 else "mid_race_reseed"


def append_row(sheet: Path, row: dict) -> Path:
    sheet.parent.mkdir(parents=True, exist_ok=True)
    new = not sheet.exists()
    with sheet.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in FIELDS})
    return sheet


def timed_attempt(race: str, attempt: int, timecode, answers: dict, wait_s: float | None = None, rehearsal: bool = False) -> dict:
    """Run the stopwatch (really) around either the operator's Enter/Enter or a scripted wait."""
    t0 = time.monotonic()
    if wait_s is None:
        input("Press Enter to STOP.")
    else:
        time.sleep(max(0.0, float(wait_s)))
    secs = round(time.monotonic() - t0, 1)
    notes = str(answers.get("notes", "")).strip()
    if rehearsal:
        notes = f"{REHEARSAL_NOTE}; {notes}" if notes else REHEARSAL_NOTE
    return {"race_id": race, "attempt": attempt, "frame_kind": frame_kind(attempt), "video_timecode_s": timecode,
            "seconds_elapsed": secs, "n_assigned": answers.get("n_assigned", ""), "n_unassigned": answers.get("n_unassigned", ""),
            "n_wrong_after_check": answers.get("n_wrong_after_check", ""), "id_cues": answers.get("id_cues", ""), "notes": notes}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", required=True)
    ap.add_argument("--attempt", type=int, default=1, help="1 = first stable wide-pan frame; 2 = mid-race re-seed")
    ap.add_argument("--sheet", default="data/od1x/sheet_seeding.csv")
    ap.add_argument("--script", default=None, help="rehearsal only: JSON with the answers and a wait_s instead of the prompts")
    a = ap.parse_args()
    if a.script:
        if not a.race.startswith("SYNTH-"):
            print("REFUSED: scripted timer rows are rehearsal rows; the race_id must start with SYNTH-")
            return 2
        ans = json.loads(Path(a.script).read_text(encoding="utf-8"))
        row = timed_attempt(a.race, a.attempt, ans.get("video_timecode_s", ""), ans, wait_s=ans.get("wait_s", 0.0), rehearsal=True)
    else:
        tc = input("video timecode of the frame (s): ").strip()
        input("Press Enter to START the stopwatch, then assign every saddle number...")
        row = timed_attempt(a.race, a.attempt, tc, {}, wait_s=None)
        row.update({
            "n_assigned": input("runners assigned: ").strip(),
            "n_unassigned": input("runners unassigned: ").strip(),
            "n_wrong_after_check": input("wrong after checking vs finish order (fill later if unknown): ").strip(),
            "id_cues": input("cues used (cloth;silks;driver;position): ").strip(),
            "notes": input("notes: ").strip(),
        })
    print(f"elapsed: {row['seconds_elapsed']} s")
    p = append_row(Path(a.sheet), row)
    print(f"appended to {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
