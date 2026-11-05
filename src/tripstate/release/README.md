# release — freeze → calibration → release tooling (D-36, §7.2, §0.2)

**Spec:** SPEC-2.0.0-draft header (promotion rule), §0.2 DoD-1…6, §6.2–6.3, §7.2, §14. **Status:** code complete and rehearsed on synthetic fixtures; **nothing here has run for real** (OD-1x and the pilot have not happened).

| Module | Input | Output | Acceptance (tests/test_promote_draft.py, tests/test_evaluate_release.py) |
|---|---|---|---|
| `freeze` | `evidence_gated.yaml`, `kill_gates.yaml`, the draft text, `SPEC_STATUS` | `FreezeReport` (problems / advisories; marker binding counts) | blocks on un-instantiated EG, KG-1…KG-4 ≠ pass, unbound `[EG]` marker, remaining `[OPEN]`; KG-5 advisory; FROZEN-with-leftovers flagged inconsistent |
| `markers` | draft text + registries | every `[EG]` marker bound to registry keys / kill-gates; frozen values substituted, provisional numbers checked against the registry | all 24 value markers of the committed draft bind; a spec↔registry provisional mismatch refuses |
| `instantiate` | OD-1x sheets (+ pilot reports) | proposed registry values with evidence strings; keys the data cannot justify are NOT proposed | synthetic sheets instantiate every entry (D-34 offsets/tolerances, cover_lat_sw = max + 0.1, D-29 target/cap with the 1.5× floor, fps, RP-5 sw_ratio confirmation) |
| `promote` | draft, decision log, provisional TS, `version.py`, registries | `SPEC-2.0.0.md` (FROZEN, D-26…D-36 in §1, zero markers, changelog row), `TS-2.0.0-frozen.yaml`, decision log (Pending → Closed), bumped `version.py`, report + diffs | refuses on un-instantiated registry / open decisions / failing gate; dry run lint-clean; real run on an isolated repo copy is idempotent ("already frozen") and leaves `freeze_check` green |
| `evaluate` | M8 store(s) + golden manifest + TS `release` namespace | DoD-1…6 with pass/fail/invalid reasons, dual headline (D-35), per-stratum tables, `evaluation.md/.json`, changelog row draft | synthetic store passes all six; undersized fixtures give the right `invalid` reasons; a differing second run fails DoD-5 |
| `synthetic_store` | threshold set, sizes | deterministic synthetic store + manifest for the dry run | two builds hash identically (DoD-5) |

CLIs: `tools/freeze_check.py`, `tools/instantiate_eg.py`, `tools/promote_draft.py`, `tools/evaluate_release.py`. Rehearsals: `make freeze-dry-run`, `make evaluate-dry-run`.
