"""tripstate — Vincennes attelé trip-state extraction pipeline.

Built against SPEC-2.0.0-draft. Module layout mirrors the spec's M0…M8.
Numeric thresholds are never constants: see tripstate.config.ThresholdSet.
"""
from tripstate.version import SCHEMA_VERSION, SPEC_VERSION

__all__ = ["SCHEMA_VERSION", "SPEC_VERSION"]
