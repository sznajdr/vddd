"""Synthetic races for end-to-end tests and tooling dry runs. Never evidence for calibration (§7)."""
from tripstate.synth.race import (
    Camera,
    RunnerScript,
    SynthRace,
    render_boxes,
    scripted_race,
    truth_frames,
)

__all__ = ["Camera", "RunnerScript", "SynthRace", "render_boxes", "scripted_race", "truth_frames"]
