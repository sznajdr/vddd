"""Synthetic races for end-to-end tests and tooling dry runs. Never evidence for calibration (§7).

`race.py`: pack-space scripts + the affine renderer (pilot tests). `track.py`, `camera.py`, `world.py`:
world-space model (stadium track in metres, pinhole grandstand camera) for the geometry studies (A1).
"""
from tripstate.synth.race import (
           Camera,
           RunnerScript,
           SynthRace,
           render_boxes,
           scripted_race,
           truth_frames,
)
from tripstate.synth.track import StadiumTrack
from tripstate.synth.world import WorldCamera, WorldRace, lateral_compression

__all__ = ["Camera", "RunnerScript", "StadiumTrack", "SynthRace", "WorldCamera", "WorldRace", "lateral_compression",
           "render_boxes", "scripted_race", "truth_frames"]
