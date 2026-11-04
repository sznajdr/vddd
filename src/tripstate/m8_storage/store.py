"""SQLite store (SPEC-2.0.0-draft §4 M8, §9; D-11, D-13, D-32).

- DDL from tripstate/schema/ddl.sql; column order from PRAGMA table_info is the canonical key order.
- JSON array columns are stored as JSON text; unordered sets are sorted on write.
- Canonical export per table = tripstate.m8_storage.canonical.canonical_jsonl over the DDL column
  order and the full primary key (which includes the version columns, so versions coexist).
- Default read paths join qc.chartable = 1. The diagnostic override exists only on
  `state_segments(..., include_unchartable=True)`; `feature_export()` has no such parameter and
  rejects it structurally (D-11).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from tripstate.m8_storage.canonical import canonical_jsonl, canonical_sha256
from tripstate.version import SCHEMA_VERSION

DDL_PATH = Path(__file__).resolve().parents[1] / "schema" / "ddl.sql"

ARRAY_COLUMNS = {"metadata_conflict_codes", "failure_codes", "conflict_codes", "source_shot_types", "candidate_states"}
UNORDERED_ARRAY_COLUMNS = {"metadata_conflict_codes", "failure_codes", "conflict_codes", "candidate_states"}
BOOL_COLUMNS = {
    "chartable", "start_handicap", "ingest_failed", "human_confirmed", "covered", "lead_uncovered_outside",
    "lead_uncovered_outside_ambiguous", "start_truncated", "end_truncated", "anchor_suspect", "id_suspect",
    "recall_suspected", "recovered", "terminal_before_final_third", "arrival_revised", "calibrated",
}
VERSION_COLUMNS = ("schema_version", "producer_version", "created_at")


class Store:
    def __init__(self, path: str | Path = ":memory:"):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.apply_schema()

    def apply_schema(self) -> None:
        self.conn.executescript(DDL_PATH.read_text(encoding="utf-8"))
        self.conn.commit()
        self.migrate_additive()

    def migrate_additive(self) -> list[tuple[str, str]]:
        """Schema-additive migration (M8 DoD; §14: new columns = minor version): add to an existing store every
        column the DDL has and the table lacks, as `ALTER TABLE … ADD COLUMN` with the DDL's type. Only nullable
        columns without a NOT NULL constraint can be added this way; anything else is a breaking change and raises.
        Returns the (table, column) pairs added; idempotent."""
        ref = sqlite3.connect(":memory:")
        ref.executescript(DDL_PATH.read_text(encoding="utf-8"))
        added: list[tuple[str, str]] = []
        for (table,) in ref.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            have = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
            for _cid, name, ctype, notnull, default, pk in ref.execute(f"PRAGMA table_info({table})"):
                if name in have:
                    continue
                if pk or (notnull and default is None):
                    raise RuntimeError(f"{table}.{name}: NOT NULL / key column cannot be added additively (breaking change = major version)")
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ctype}" + (f" DEFAULT {default}" if default is not None else ""))
                added.append((table, name))
        ref.close()
        if added:
            self.conn.commit()
        return added

    # --- schema introspection -------------------------------------------------------------
    def columns(self, table: str) -> list[str]:
        return [r["name"] for r in self.conn.execute(f"PRAGMA table_info({table})")]

    def primary_key(self, table: str) -> list[str]:
        rows = [r for r in self.conn.execute(f"PRAGMA table_info({table})") if r["pk"] > 0]
        return [r["name"] for r in sorted(rows, key=lambda r: r["pk"])]

    def tables(self) -> list[str]:
        return [r["name"] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    # --- writes ---------------------------------------------------------------------------
    @staticmethod
    def _encode(col: str, v: Any) -> Any:
        if v is None:
            return None
        if col in ARRAY_COLUMNS:
            items = sorted(v) if col in UNORDERED_ARRAY_COLUMNS else list(v)
            return json.dumps(items, ensure_ascii=False)
        if isinstance(v, bool):
            return int(v)
        return v

    def insert(self, table: str, rows: list[dict], *, producer_version: str, created_at: str,
               extractor_version: str | None = None, threshold_set_version: str | None = None,
               schema_version: str = SCHEMA_VERSION) -> int:
        cols = self.columns(table)
        colset = set(cols)
        n = 0
        for r in rows:
            extra = set(r) - colset
            if extra:
                raise ValueError(f"{table}: columns not in schema: {sorted(extra)}")
            full = dict(r)
            full.setdefault("schema_version", schema_version)
            full.setdefault("producer_version", producer_version)
            full.setdefault("created_at", created_at)
            if "extractor_version" in colset and "extractor_version" not in full:
                full["extractor_version"] = extractor_version
            if "threshold_set_version" in colset and "threshold_set_version" not in full:
                full["threshold_set_version"] = threshold_set_version
            keys = [c for c in cols if c in full]
            self.conn.execute(
                f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join('?' for _ in keys)})",
                [self._encode(k, full[k]) for k in keys],
            )
            n += 1
        self.conn.commit()
        return n

    # --- reads ----------------------------------------------------------------------------
    def _decode(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        for c, v in d.items():
            if v is None:
                continue
            if c in ARRAY_COLUMNS and isinstance(v, str):
                d[c] = json.loads(v)
            elif c in BOOL_COLUMNS:
                d[c] = bool(v)
        return d

    def rows(self, table: str, where: dict[str, Any] | None = None) -> list[dict]:
        sql = f"SELECT * FROM {table}"
        params: list[Any] = []
        if where:
            sql += " WHERE " + " AND ".join(f"{k} = ?" for k in where)
            params = [self._encode(k, v) for k, v in where.items()]
        return [self._decode(r) for r in self.conn.execute(sql, params)]

    def state_segments(self, race_id: str | None = None, producer_version: str | None = None,
                       include_unchartable: bool = False) -> list[dict]:
        """Default: chartable races only. include_unchartable=True is DIAGNOSTIC ONLY (M7 DoD)."""
        sql = ("SELECT s.* FROM state_segments s JOIN qc q ON q.race_id = s.race_id AND q.producer_version = s.producer_version"
               if not include_unchartable else "SELECT s.* FROM state_segments s")
        conds, params = [], []
        if not include_unchartable:
            conds.append("q.chartable = 1")
        if race_id is not None:
            conds.append("s.race_id = ?"); params.append(race_id)
        if producer_version is not None:
            conds.append("s.producer_version = ?"); params.append(producer_version)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        return [self._decode(r) for r in self.conn.execute(sql, params)]

    def feature_export(self, producer_version: str | None = None, **kwargs: Any) -> list[dict]:
        """Feature-engineering entry point: chartable only, no override accepted (D-11, structurally)."""
        if kwargs:
            raise TypeError(f"feature_export accepts no override parameters: {sorted(kwargs)}")
        return self.state_segments(producer_version=producer_version, include_unchartable=False)

    # --- canonical export (DoD-5) ---------------------------------------------------------
    def canonical(self, table: str, producer_version: str | None = None) -> str:
        where = {"producer_version": producer_version} if producer_version else None
        return canonical_jsonl(self.rows(table, where), self.columns(table), self.primary_key(table),
                               unordered_set_cols=UNORDERED_ARRAY_COLUMNS)

    def canonical_sha(self, table: str, producer_version: str | None = None) -> str:
        return canonical_sha256(self.canonical(table, producer_version))

    def canonical_all(self, producer_version: str | None = None) -> dict[str, str]:
        return {t: self.canonical_sha(t, producer_version) for t in self.tables()}
