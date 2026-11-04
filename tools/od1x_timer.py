#!/usr/bin/env python3
"""OD-1x stopwatch for step 1 (timed seeding). Appends one row per attempt to sheet_seeding.csv.

usage: od1x_timer.py --race 20261103-R1-C4 --attempt 1 --sheet data/od1x/sheet_seeding.csv
Press Enter to start, Enter again to stop, then answer the prompts.
"""
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

FIELDS = ["race_id", "attempt", "frame_kind", "video_timecode_s", "seconds_elapsed",
          "n_assigned", "n_unassigned", "n_wrong_after_check", "id_cues", "notes"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", required=True)
    ap.add_argument("--attempt", type=int, default=1, help="1 = first stable wide-pan frame; 2 = mid-race re-seed")
    ap.add_argument("--sheet", default="data/od1x/sheet_seeding.csv")
    a = ap.parse_args()
    tc = input("video timecode of the frame (s): ").strip()
    input("Press Enter to START the stopwatch, then assign every saddle number...")
    t0 = time.monotonic()
    input("Press Enter to STOP.")
    secs = round(time.monotonic() - t0, 1)
    print(f"elapsed: {secs} s")
    row = {
        "race_id": a.race, "attempt": a.attempt,
        "frame_kind": "first_stable_wide_pan" if a.attempt == 1 else "mid_race_reseed",
        "video_timecode_s": tc, "seconds_elapsed": secs,
        "n_assigned": input("runners assigned: ").strip(),
        "n_unassigned": input("runners unassigned: ").strip(),
        "n_wrong_after_check": input("wrong after checking vs finish order (fill later if unknown): ").strip(),
        "id_cues": input("cues used (cloth;silks;driver;position): ").strip(),
        "notes": input("notes: ").strip(),
    }
    p = Path(a.sheet)
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"appended to {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
