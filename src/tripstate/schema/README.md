# schema — §9 relational shape

`ddl.sql`: the SQLite DDL applied by `tripstate.m8_storage.Store` (column order = canonical key order; every versioned artifact key includes `producer_version`; CV uniqueness adds `extractor_version` + `threshold_set_version`; `created_at` is operational and excluded from the canonical export). `enums.py`: the closed enums of §2, §9, §10 — extending one is a version bump.

Changes: additive nullable columns (minor version) are picked up by existing stores through `Store.migrate_additive()` (first use: RP-18 `id_assignments.seed_x_px/seed_y_px/seed_box_ref`, ledger L-51); anything NOT NULL or key-affecting is a breaking change (major) and the migration refuses it. `schema_version` equals the governing spec version (`tripstate.version.SCHEMA_VERSION`).
