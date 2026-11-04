"""M7 — QC & coverage (SPEC-2.0.0-draft §10, §6.2 per-stratum yield; D-11, D-35).

Implemented (reference): gate evaluation Q-1…Q-7 with the closed failure-code set, per-stratum
chartable yield with the D-35 review trigger, SHOT_GAP events and coverage fractions.
"""
from tripstate.m7_qc.gates import (
           FAILURE_CODES,
           GateResult,
           RaceQCInput,
           evaluate_gates,
           stratum_yield,
)
from tripstate.m7_qc.shot_gaps import Shot, coverage_fractions, shot_gap_events

__all__ = [
           "FAILURE_CODES",
           "GateResult",
           "RaceQCInput",
           "Shot",
           "coverage_fractions",
           "evaluate_gates",
           "shot_gap_events",
           "stratum_yield",
]
