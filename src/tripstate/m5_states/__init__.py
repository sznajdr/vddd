"""M5 — State machine (SPEC-2.0.0-draft §2.3–2.4, §3.4; D-27).

Implemented (reference): per-frame base-state classification incl. lead_uncovered_outside and the
DETACHED overlay; tier hysteresis; min-duration smoothing of cover and states; segment emission.
"""
from tripstate.m5_states.classify import (
           RunnerGeom,
           RunnerState,
           assign_lead,
           classify_frame,
           detached_overlay,
)
from tripstate.m5_states.smoothing import FrameGeom, apply_tier_hysteresis, chart_race, smooth_runs

__all__ = [
           "FrameGeom",
           "RunnerGeom",
           "RunnerState",
           "apply_tier_hysteresis",
           "assign_lead",
           "chart_race",
           "classify_frame",
           "detached_overlay",
           "smooth_runs",
]
