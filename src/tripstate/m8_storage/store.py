"""SQLite + parquet persistence — STUB. DDL lives in tripstate/schema/ddl.sql.

Contract (§4 M8): round-trip integrity; canonical export byte-identical under same inputs and
versions (DoD-5, quantized per D-32); two extractor versions coexist queryably; default export
views join qc.chartable = true; no feature-export path exposes include_unchartable.
"""


def open_store(path):
    raise NotImplementedError("M8 store: SPEC-2.0.0-draft §4 M8 / §9; apply schema/ddl.sql")
