"""Evaluation (SPEC-2.0.0-draft §6.2–6.4; D-27, D-31). Pure functions over segment rows."""
from tripstate.evaluation.identity_audit import (
    AuditPlan,
    audit_seed,
    pass_probability,
    plan_audit,
    score_audit,
)
from tripstate.evaluation.metrics import (
    REST_STATES,
    break_candidate_recall,
    edit_score,
    f1_at_k,
    headline_score,
    macro_iou,
    mask_iou,
    segment_iou,
    wilson_ci,
)
from tripstate.evaluation.scoring import (
    RaceScore,
    SetScore,
    observability_mask,
    score_race,
    score_set,
)

__all__ = [
    "REST_STATES",
    "AuditPlan",
    "RaceScore",
    "SetScore",
    "audit_seed",
    "break_candidate_recall",
    "edit_score",
    "f1_at_k",
    "headline_score",
    "macro_iou",
    "mask_iou",
    "observability_mask",
    "pass_probability",
    "plan_audit",
    "score_audit",
    "score_race",
    "score_set",
    "segment_iou",
    "wilson_ci",
]
