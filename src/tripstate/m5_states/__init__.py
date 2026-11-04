"""M5 — State machine (SPEC-2.0.0-draft §2.3–2.4, §3.4; D-27).

Implemented (reference): per-frame base-state classification table incl. lead_uncovered_outside.
Stub: temporal smoothing + segment emission.
"""
from tripstate.m5_states.classify import RunnerGeom, RunnerState, classify_frame

__all__ = ["RunnerGeom", "RunnerState", "classify_frame"]
