"""Throwaway pilot stack (protocols/PILOT-5; RP-2 exemption from G-1…G-3).

Pluggable backends behind small protocols so the same pipeline runs on synthetic video here
(oracle / blob / IoU-tracker backends) and on real replays with Grounding DINO / OWLv2 /
Ultralytics / SAM 2 adapters (lazily imported). Outputs carry producer_kind = pilot_throwaway.
"""
from tripstate.pilot.frames import FrameSource, encode_frames, render_synth_video
from tripstate.pilot.run import PilotRaceReport, run_pilot_race

__all__ = ["FrameSource", "PilotRaceReport", "encode_frames", "render_synth_video", "run_pilot_race"]
