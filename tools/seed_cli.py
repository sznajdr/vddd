#!/usr/bin/env python3
"""Seeding tool SKELETON (M3 tool DoD; D-16; DR-12). OpenCV window + keyboard. Not functional yet.

Keymap (normative target, §4 M3 tool DoD):
  space      play/pause            ,/.    step -1/+1 frame        [ / ]   jump prev/next flagged cut
  1-9,0      playback speed x1..x? (>= 2x available; auto-slowdown at flagged events)
  click      select runner under cursor, then type saddle number + Enter
  o          confirm proposed travel-direction + rail-side (1 key when both correct)
  O / R      correct travel direction / rail side
  t / e      capture t_0 / t_end anchor at current frame        r   mark "possible recall" (EC-14)
  a / x      accept / reject current break candidate            f   confirm first-past runner
  q          write chart + QC + human-minutes, quit

Human-minutes are logged automatically from the first keypress to `q`.
Pilot use (RP-2): this skeleton is the operator surface for the throwaway pilot once the
play/step/click/anchor keys are implemented; everything else can wait for M3 proper.
"""
from __future__ import annotations

import sys


def main() -> int:
    try:
        import cv2  # noqa: F401
    except ImportError:
        print("opencv-python not installed: pip install -e '.[cv]'", file=sys.stderr)
        return 2
    print(__doc__)
    print("NOT IMPLEMENTED: build the play/step/click/anchor loop first (pilot needs only those).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
