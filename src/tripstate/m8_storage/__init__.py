"""M8 — Storage & versioning (SPEC-2.0.0-draft §9; D-13, D-32).

Implemented (reference): canonical JSONL export with fixed-decimal quantization, deterministic
ordinal IDs, aggregate SHA-256. Stub: SQLite/parquet persistence (DDL in tripstate/schema/ddl.sql).
"""
from tripstate.m8_storage.canonical import (
    EXCLUDED_OPERATIONAL,
    canonical_jsonl,
    canonical_sha256,
    ordinal_ids,
    quantize,
)

__all__ = ["EXCLUDED_OPERATIONAL", "canonical_jsonl", "canonical_sha256", "ordinal_ids", "quantize"]
