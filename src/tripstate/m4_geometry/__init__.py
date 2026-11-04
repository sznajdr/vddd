"""M4 — Pack-space geometry (SPEC-2.0.0-draft §2.2, §3; D-26).

Implemented (reference, evidence-independent): tier clustering with span bound + largest-gap
split, absolute-tier attachment (EC-13), D-26 cover predicate. Stub: principal axis /
projection from tracklets (needs M2/M3 output).
"""
from tripstate.m4_geometry.tiering import (
    absolute_tiers,
    cluster_tiers,
    covered,
    covered_all,
    split_by_span,
)

__all__ = ["absolute_tiers", "cluster_tiers", "covered", "covered_all", "split_by_span"]
