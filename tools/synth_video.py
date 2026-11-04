#!/usr/bin/env python3
"""Render the scripted synthetic race to a real video + truth + seeds + tier labels + a headless seeding script,
so the seeding tool and the pilot pipeline can be exercised before any replay exists.

  synth_video.py --out data/synth [--duration 20] [--size 640x360]
Then:
  python tools/seed_cli.py data/synth/synth.mp4 --race SYNTH-1 --out data/synth/session --script data/synth/seed_script.json
  python tools/pilot_run.py --video data/synth/synth.mp4 --race SYNTH-1 --session data/synth/session/session.json \
         --truth data/synth/synth.mp4.truth.json --path seeded --propagator oracle --out data/pilot5/SYNTH-1
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.pilot.frames import render_synth_video, truth_boxes_from_json
from tripstate.synth import scripted_race, truth_frames


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--duration", type=float, default=20.0)
    ap.add_argument("--size", default="640x360"); ap.add_argument("--seed-frame", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    w, h = (int(x) for x in a.size.lower().split("x"))
    race = scripted_race(duration_s=a.duration)
    video = out / "synth.mp4"
    truth = render_synth_video(race, video, size=(w, h))
    tb = truth_boxes_from_json(truth)
    seeds = [{"frame": a.seed_frame, "saddle_no": s, "x": (b.x1 + b.x2) / 2, "y": (b.y1 + b.y2) / 2} for s, b in sorted(tb[a.seed_frame].items())]
    (out / "seeds.json").write_text(json.dumps(seeds, indent=1))
    tg, _ = truth_frames(race)
    n = len(race.frames())
    with (out / "tier_labels.csv").open("w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["race_id", "frame", "saddle_no", "tier_human"])
        for fr in range(0, n, 25):
            for s in truth["saddles"]:
                if tg[s][fr].detected:
                    wr.writerow(["SYNTH-1", fr, s, tg[s][fr].tier])
    script = [{"do": "key", "key": "o"}, {"do": "key", "key": "t"}, {"do": "goto", "frame": a.seed_frame}]
    for sd in seeds:
        script += [{"do": "click", "x": sd["x"], "y": sd["y"]}, {"do": "type", "number": sd["saddle_no"]}]
    script += [{"do": "key", "key": "8"}, {"do": "key", "key": " "}, {"do": "tick", "n": n}, {"do": "resolve_flags"},
               {"do": "key", "key": " "}, {"do": "tick", "n": n}, {"do": "goto", "frame": n - 1},
               {"do": "key", "key": "e"}, {"do": "key", "key": "f"}, {"do": "type", "number": 1}, {"do": "key", "key": "q"}]
    (out / "seed_script.json").write_text(json.dumps(script, indent=1))
    (out / "race.json").write_text(json.dumps({"race_id": "SYNTH-1", "fps": race.fps, "n_frames": n, "t0_s": race.t0, "tend_s": race.tend,
                                               "saddles": truth["saddles"], "start_type": "autostart", "travel_sign": 1, "rail_side": "right_of_travel",
                                               "official_elapsed_norm_s": race.tend - race.t0}, indent=1))
    print(f"wrote {video} ({n} frames @ {race.fps} fps, {w}x{h}), truth, seeds.json, tier_labels.csv, seed_script.json, race.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
