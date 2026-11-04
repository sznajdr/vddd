"""M4 — Pack-space geometry (SPEC-2.0.0-draft §2.2, §3; D-26).

Implemented (reference, evidence-independent): tier clustering with span bound + largest-gap
split, absolute-tier attachment (EC-13), D-26 cover predicate, principal-axis projection from
boxes (ShotProjector). Pixel-space rail detection is supplied by the caller.
"""
from tripstate.m4_geometry.projection import (
    Box,
    FrameGeometry,
    RunnerGeometry,
    ShotCalibration,
    ShotProjector,
    frames_from_json,
    frames_to_json,
    lateral_unit,
    to_frame_geoms,
)
from tripstate.m4_geometry.tiering import (
    absolute_tiers,
    cluster_tiers,
    covered,
    covered_all,
    split_by_span,
)

__all__ = ["Box", "FrameGeometry", "RunnerGeometry", "ShotCalibration", "ShotProjector", "absolute_tiers",
           "cluster_tiers", "covered", "covered_all", "frames_from_json", "frames_to_json", "lateral_unit", "split_by_span",
           "to_frame_geoms"]
