# spec/ — the single source of truth (§14)

| File | Status | Role |
|---|---|---|
| `SPEC-1.2.0.md` | FROZEN 2026-07-25 | last frozen 1.x spec; diff base of 2.0.0. The 1.x line is closed. |
| `SPEC-2.0.0-draft.md` | DRAFT (D-36) | the governing spec for all current work. **Generated**: `tools/cut_draft.py` applies the ledger to 1.2.0; `--check` runs in CI. Never edit it by hand — add a ledger row and a `rep(...)` edit, then regenerate. |
| `SPEC-2.0.0-draft-LEDGER.md` | informative | every edit versus 1.2.0 (L-01…L-45 the cut, L-46…L-51 the delegated decisions and the RP-18 schema task), with its basis and gate |
| `RECON-2.0.0.md`, `RECON-2.0.0-patches.md` | historical | the reconciliation that defined the 2.0.0 delta and the defects found afterwards; verdicts now live in `docs/decisions/` |
| `reviews/` | historical | external review of 1.2.0 |
| `decisions/DECISION-LOG.md` | normative | D-01…D-25 closed; D-26…D-36 pending until the freeze, then appended to §1 by `tools/promote_draft.py` |
| `registers/evidence_gated.yaml` | normative | every provisional number that blocks the freeze, with its instrument and rule; filled by `tools/instantiate_eg.py`, checked by `tools/freeze_check.py` |
| `registers/kill_gates.yaml` | normative | KG-1…KG-5 (§0.4); statuses written by `tools/pilot_report.py` |
| `registers/out_of_scope.md` | informative | the §12 register with re-entry versions |

Lifecycle: draft (now) → `tools/freeze_check.py` exit 0 → `tools/promote_draft.py` writes `SPEC-2.0.0.md` FROZEN in one commit → calibration (`tools/calibrate.py`) and release evaluation (`tools/evaluate_release.py`) append §14 changelog rows. `make lint-spec` checks table hygiene, decision references, EG flags and draft reproducibility; a FROZEN file may carry no `[EG]` or `[OPEN]` marker.
