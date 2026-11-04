# Build prompt template (one per module; cite the spec version)

```
You are building module <Mx> of the Vincennes attelé trip-state pipeline against SPEC-2.0.0-draft
(spec/SPEC-2.0.0-draft.md, which is spec/SPEC-1.2.0.md plus the delta ledger).

Read, in order: CLAUDE.md; spec/SPEC-1.2.0.md §<sections>; the ledger rows <L-xx…>;
spec/decisions/DECISION-LOG.md; src/tripstate/<module>/README.md.

Contract: Input / Output / Acceptance / DoD as stated in the module README. Do not change them.
Thresholds: every numeric cutoff goes under namespace `<module>` in config/thresholds/TS-*.yaml.
Prime directive: FLAG AND DEGRADE, NEVER GUESS.
Determinism: no UUIDs, no wall-clock in canonical payloads, floats unquantized inside logic.
Deliverables: implementation under src/tripstate/<module>/, tests under tests/ that encode the
acceptance fixture, README status updated, `make test && make lint-spec` green.
Do not: touch other modules' contracts, start golden charting, calibrate thresholds, train M2
before the freeze.
```
