# M8 — Storage & Versioning

**Spec:** §9, §4 M8; ledger L-37…L-40; D-13, D-32. **Status:** canonical export and SQLite store implemented and tested: DDL applied from `../schema/ddl.sql`, JSON array columns, chartable-only default reads, diagnostic override only on `state_segments()`, `feature_export()` rejects overrides structurally, per-table canonical SHA with version coexistence.

| | |
|---|---|
| Input | All module outputs. |
| Output | SQLite + parquet sidecars; export views; canonical JSONL per table. |
| Acceptance | Round-trip integrity; canonical export byte-identical under same inputs/versions; two extractor versions coexist. |
| DoD | Schema-additive migration = minor; breaking = major; default views join `chartable = true`. |

Quantization (L-39): `_frac` 6 dp, `_s` 3 dp, `_sl`/`_sw`/`conf` 4 dp. Applied only in the export.

`determinism.py` (C3, D-32): `fingerprint()` → the `versions.determinism_env` JSON (actual versions and flags, null when absent, key-sorted); `versions_row()` for `Store.insert`; CLI `tools/env_fingerprint.py`.
