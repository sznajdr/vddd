"""Canonical deterministic payload (SPEC-2.0.0-draft §9 as amended by L-39; D-32).

Rules: UTF-8, NFC, LF, keys in schema order, rows sorted by the full versioned primary key,
JSON literals for NULL/bool, finite floats quantized to fixed decimals BEFORE hashing
(SW/SL/conf 4 dp; seconds 3 dp; fractions 6 dp), NaN/inf forbidden, unordered sets sorted,
operational timestamps excluded, sidecars by SHA-256. Quantization lives ONLY here — never
inside comparisons or threshold logic.
"""
from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

EXCLUDED_OPERATIONAL = frozenset({"created_at", "reviewed_at", "human_minutes", "operator_wallclock"})

# Decimal places by column-name suffix / class (L-39).
DECIMALS_BY_SUFFIX: tuple[tuple[str, int], ...] = (
    ("_frac", 6),
    ("_s", 3),        # seconds (video timecodes, deltas)
    ("_sl", 4),
    ("_sw", 4),
    ("conf", 4),
    ("confidence", 4),
)
DEFAULT_DECIMALS = 6


def decimals_for(column: str) -> int:
    for suffix, d in DECIMALS_BY_SUFFIX:
        if column.endswith(suffix):
            return d
    return DEFAULT_DECIMALS


def quantize(value: float, decimals: int) -> str:
    """Fixed-decimal string, round-half-even, no exponent, '-0.000' normalized to '0.000'."""
    if isinstance(value, bool):
        raise TypeError("bool is not a float")
    if not math.isfinite(value):
        raise ValueError("NaN/inf forbidden in canonical payload; use NULL")
    q = Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_EVEN)
    s = format(q, "f")
    if s.startswith("-") and float(s) == 0.0:
        s = s[1:]
    return s


def _canon_value(col: str, v: Any, unordered_set_cols: frozenset[str]) -> Any:
    if v is None or isinstance(v, (bool, int)):
        return v
    if isinstance(v, float):
        return quantize(v, decimals_for(col))
    if isinstance(v, str):
        return unicodedata.normalize("NFC", v)
    if isinstance(v, (list, tuple)):
        items = [_canon_value(col, x, unordered_set_cols) for x in v]
        return sorted(items, key=json.dumps) if col in unordered_set_cols else items
    if isinstance(v, bytes):
        return hashlib.sha256(v).hexdigest()
    raise TypeError(f"unsupported type {type(v).__name__} in column {col}")


def canonical_jsonl(
    rows: Iterable[dict[str, Any]],
    schema_order: Sequence[str],
    primary_key: Sequence[str],
    unordered_set_cols: Iterable[str] = ("metadata_conflict_codes", "failure_codes"),
) -> str:
    """Rows -> canonical JSONL text. Columns not in schema_order are rejected; excluded
    operational columns are dropped; missing columns are emitted as null."""
    uns = frozenset(unordered_set_cols)
    cols = [c for c in schema_order if c not in EXCLUDED_OPERATIONAL]
    canon: list[dict[str, Any]] = []
    for r in rows:
        extra = set(r) - set(schema_order)
        if extra:
            raise ValueError(f"columns not in schema order: {sorted(extra)}")
        canon.append({c: _canon_value(c, r.get(c), uns) for c in cols})
    def _key(row: dict[str, Any]):
        return tuple((row[k] is None, row[k] if row[k] is not None else "") for k in primary_key)
    canon.sort(key=_key)
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":"), allow_nan=False) for r in canon]
    return "\n".join(lines) + ("\n" if lines else "")


def canonical_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ordinal_ids(
    records: list[dict[str, Any]],
    id_field: str,
    leading_sort_field: str,
) -> list[dict[str, Any]]:
    """Deterministic zero-based ordinal IDs within one parent key (§9): sort by the leading
    field, then by the full canonical record bytes with the ID omitted (NULL sorts last)."""
    def _k(r: dict[str, Any]):
        lead = r.get(leading_sort_field)
        body = {k: v for k, v in r.items() if k != id_field}
        return (lead is None, lead if lead is not None else 0, json.dumps(body, sort_keys=True, default=str))
    out = []
    for i, r in enumerate(sorted(records, key=_k)):
        r2 = dict(r)
        r2[id_field] = i
        out.append(r2)
    return out
