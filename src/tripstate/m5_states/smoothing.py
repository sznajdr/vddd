"""Temporal smoothing + segment emission — STUB (SPEC-2.0.0-draft §3.4).

Contract: min_state_s merge by confidence-weighted vote between confident geometric states;
tier_hysteresis_s on tier transitions; NOT_VISIBLE/UNKNOWN/SHOT_GAP/BREAKING keep observed
boundaries; derived attributes (incl. lead_uncovered_outside) recomputed after smoothing;
D-26 cover predicate smoothed with the same min-duration rule (L-11).
"""


def smooth_states(*args, **kwargs):
    raise NotImplementedError("M5 smoothing: SPEC-2.0.0-draft §3.4; build after M4 projection exists")
