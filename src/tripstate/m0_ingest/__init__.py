"""M0 — Ingest & Normalization (SPEC-2.0.0-draft §4 M0).

Implemented: metadata normalization rules 1–6 (evidence-independent, allowed under DRAFT).
Stub: video normalization (needs ffmpeg + replays).
"""
from tripstate.m0_ingest.metadata import (
    CONFLICT_CODES,
    RaceIn,
    RaceNorm,
    RunnerIn,
    RunnerNorm,
    normalize_race,
    normalize_runner_time,
)

__all__ = [
    "CONFLICT_CODES", "RaceIn", "RaceNorm", "RunnerIn", "RunnerNorm",
    "normalize_race", "normalize_runner_time",
]
