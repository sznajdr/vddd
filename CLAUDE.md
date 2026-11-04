# Instructions for coding agents in this repository

1. **Reference a spec version in every change.** Build prompts and PR descriptions cite `SPEC-2.0.0-draft` (or `SPEC-1.2.0` for the diff base). The spec is the single source of truth (§14).
2. **Do not re-litigate closed decisions** (D-01…D-25 in `spec/decisions/DECISION-LOG.md`). Proposals conflicting with them are rejected with a pointer to the entry. D-26…D-36 are pending until the freeze; they are the agreed direction and may be built against, not reopened.
3. **DRAFT rule (D-36).** Until `spec/SPEC-2.0.0-draft.md` is promoted: M0, schema, and tooling scaffolds MAY be built. Golden charting, calibration and M2 training MUST NOT begin. `tools/freeze_check.py` says whether the freeze is allowed.
4. **Numbers are config.** Every numeric cutoff that can change an emitted artifact lives in `config/thresholds/TS-*.yaml` under a namespaced key (D-18, §7.1). A provisional number carries `eg: true` in the YAML and an `[EG: OD-1x]` marker in the spec. Never hard-code a threshold.
5. **Prime directive in code:** prefer `LOW_CONF` / `UNKNOWN` / `NOT_VISIBLE` / `unchartable` / `NULL` over any inferred value. A function that cannot decide returns the abstention value and a reason code.
6. **Determinism (D-32):** no random UUIDs, no insertion-order IDs, no wall-clock in canonical payloads. Floats are quantized only in the canonical export, never inside comparisons.
7. **Tests before acceptance.** Each module directory has a README with Input / Output / Acceptance / DoD. A module is not "done" until its acceptance fixture passes; stubs raise `NotImplementedError` with the spec section in the message.
8. **Human protocols are not code.** `protocols/` are followed by the owner with a stopwatch and a notebook; tools in `tools/` only make recording easier.
9. Run `make test && make lint-spec` before proposing a change.
