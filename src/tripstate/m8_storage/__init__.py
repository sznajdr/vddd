"""M8 — Storage & versioning (SPEC-2.0.0-draft §9; D-13, D-32).

Implemented: canonical JSONL export with fixed-decimal quantization, deterministic ordinal IDs,
aggregate SHA-256; SQLite store applying schema/ddl.sql with chartable-only default reads.
"""
from tripstate.m8_storage.canonical import (
    EXCLUDED_OPERATIONAL,
    canonical_jsonl,
    canonical_sha256,
    ordinal_ids,
    quantize,
)
from tripstate.m8_storage.store import Store

__all__ = ["EXCLUDED_OPERATIONAL", "Store", "canonical_jsonl", "canonical_sha256", "ordinal_ids", "quantize"]
