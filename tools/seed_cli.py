#!/usr/bin/env python3
"""Seeding tool (M3 tool DoD; D-16): OpenCV window around `tripstate.seeding.SeedingSession`.

  seed_cli.py VIDEO --race ID --start-type volte --start-format volte_handicap --out data/pilot5/ID/
             [--flags flags.json] [--candidates cands.json] [--tracks tracks.json] [--cap 8]
  seed_cli.py VIDEO --race ID ... --script actions.json      # headless replay (no display needed)

Window: frames decoded through ffmpeg (no OpenCV video backend needed). Overlay: playhead time,
speed, unresolved flags, pending number entry, orientation proposal, anchors, human-minutes and
over-budget warning. Keymap: see tripstate/seeding/session.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.pilot.frames import FrameSource
from tripstate.seeding import Candidate, Flag, SeedingSession
from tripstate.seeding.session import Orientation

CV_KEYS = {32: " ", 44: ",", 46: ".", 91: "[", 93: "]", 27: "Escape", 13: "Enter", 10: "Enter"}


def build_session(a, n_frames: int, fps: float) -> SeedingSession:
    flags = [Flag(**f) for f in json.loads(Path(a.flags).read_text())] if a.flags else []
    cands = [Candidate(**c) for c in json.loads(Path(a.candidates).read_text())] if a.candidates else []
    orient = Orientation(a.travel_sign, a.rail_side, 0.5)
    return SeedingSession(a.race, n_frames, fps, start_type=a.start_type, start_format=a.start_format,
                          budget_cap_min=a.cap, flags=flags, candidates=cands, orientation=orient)


def run_script(s: SeedingSession, actions: list[dict]) -> None:
    for act in actions:
        kind = act["do"]
        if kind == "key":
            s.key(act["key"])
        elif kind == "click":
            s.click(act["x"], act["y"])
        elif kind == "type":
            for ch in str(act["number"]):
                s.key(ch)
            s.key("Enter")
        elif kind == "tick":
            for _ in range(int(act.get("n", 1))):
                s.tick()
        elif kind == "goto":
            s.index = int(act["frame"])


def run_window(s: SeedingSession, src: FrameSource, tracks: dict | None) -> None:
    try:
        import cv2
    except ImportError:
        print("OpenCV not installed: pip install opencv-python  (or use --script for headless replay)", file=sys.stderr)
        raise SystemExit(2)
    win = f"seed: {s.race_id}"
    cv2.namedWindow(win)
    cv2.setMouseCallback(win, lambda ev, x, y, *_: s.click(x, y) if ev == cv2.EVENT_LBUTTONDOWN else None)
    frames = src.frame_cache()
    while s.finished_at is None:
        img = frames[s.index][:, :, ::-1].copy()  # RGB -> BGR
        if tracks:
            for sad, box in tracks.get(str(s.index), {}).items():
                x1, y1, x2, y2 = (int(v) for v in box)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 1)
                cv2.putText(img, str(sad), (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        hud = [f"f={s.index} t={s.t_s:.2f}s x{s.speed} {'PLAY' if s.playing else 'PAUSE'}",
               f"flags open={len(s.unresolved_flags())} seeds={len(s.seeds)} t0={s.t0_frame} tend={s.tend_frame}",
               (f"enter number for {'seed' if s.awaiting == 'seed' else 'first past'}: {s.number_buffer}_" if s.awaiting else s.start_prompt()),
               f"minutes={0 if s.human_minutes() is None else s.human_minutes():.1f}" + ("  OVER BUDGET" if s.over_budget() else "")]
        for i, line in enumerate(hud + s.messages[-2:]):
            cv2.putText(img, line, (8, 18 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.imshow(win, img)
        k = cv2.waitKey(int(1000 / s.fps)) & 0xFF
        if k != 255:
            s.key(CV_KEYS.get(k, chr(k)))
        s.tick()
    cv2.destroyAllWindows()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--race", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--start-type", default="autostart", choices=["autostart", "volte"])
    ap.add_argument("--start-format", default="autostart", choices=["autostart", "volte_flat", "volte_handicap"])
    ap.add_argument("--cap", type=float, default=8.0); ap.add_argument("--flags"); ap.add_argument("--candidates"); ap.add_argument("--tracks")
    ap.add_argument("--travel-sign", type=int, default=1); ap.add_argument("--rail-side", default="right_of_travel")
    ap.add_argument("--script", help="JSON list of actions for headless replay")
    a = ap.parse_args()
    src = FrameSource(Path(a.video))
    s = build_session(a, src.n_frames, src.fps)
    if a.script:
        s.headless = True
        run_script(s, json.loads(Path(a.script).read_text()))
        if s.finished_at is None:
            s.key("q")
    else:
        tracks = json.loads(Path(a.tracks).read_text()) if a.tracks else None
        run_window(s, src, tracks)
    p = s.write(Path(a.out))
    r = s.result()
    print(f"wrote {p}: {len(r['seeds'])} seeds, anchors {r['anchors']['t0_frame']}/{r['anchors']['tend_frame']}, "
          f"{r['human_minutes'] and round(r['human_minutes'], 2)} min{' OVER BUDGET' if r['over_budget'] else ''}"
          + ("  [headless replay: wall-clock not meaningful]" if r["headless"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
