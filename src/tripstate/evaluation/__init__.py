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

__all__ = [
    "REST_STATES",
    "AuditPlan",
    "audit_seed",
    "break_candidate_recall",
    "edit_score",
    "f1_at_k",
    "headline_score",
    "macro_iou",
    "mask_iou",
    "pass_probability",
    "plan_audit",
    "score_audit",
    "segment_iou",
    "wilson_ci",
]
