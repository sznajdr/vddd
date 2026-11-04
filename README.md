# Vincennes Attelé Trip-State Extraction — project repository

Extract per-horse **trip-state charts** (cover, width tier, position rank, breaks)
from Equidia broadcast replays of Vincennes trot attelé races, as overlay features
for a downstream prediction model.

The governing document is the spec in `spec/`. Everything else in this repository
exists to (a) freeze that spec on evidence instead of assumption, and (b) build the
pipeline against it once frozen.

## Where things are

| Path | What it is | Normative? |
|---|---|---|
| `spec/SPEC-1.2.0.md` | Last FROZEN spec. Diff base for 2.0.0. The 1.x line is closed. | Yes (superseded on freeze of 2.0.0) |
| `spec/SPEC-2.0.0-draft.md` | DRAFT spec, full prose, cut from 1.2.0 by `tools/cut_draft.py` (reproducible; `--check` runs in CI). Agents MAY build M0, schema, tooling against it. Golden charting and calibration MUST NOT begin. | Draft |
| `spec/SPEC-2.0.0-draft-LEDGER.md` | The edit ledger (L-01…L-45) the cut applies; the audit trail of every change versus 1.2.0. | Informative |
| `spec/RECON-2.0.0.md` | Reconciliation of 1.2.0 × review × drill queue. Defines the 2.0.0 delta. | Informative |
| `spec/RECON-2.0.0-patches.md` | Defects and gaps found in RECON after it was written; applied when the draft is cut. | Informative |
| `spec/reviews/` | External reviews. | Informative |
| `spec/decisions/DECISION-LOG.md` | D-01…D-25 (closed) and D-26…D-36 (pending, appended at freeze). | Yes |
| `spec/registers/evidence_gated.yaml` | Every provisional number that blocks the freeze, with its instantiation rule. Machine-checked by `tools/freeze_check.py`. | Yes |
| `spec/registers/kill_gates.yaml` | Project abort criteria (§0.4). | Yes |
| `config/thresholds/` | Versioned threshold sets (`TS-x.y.z.yaml`). Never constants in code (D-18). The `release` / `calibration` namespaces hold the DoD floors and §7.2 constraints. | Yes |
| `config/calibration/search-space.yaml` | Which threshold keys §7.2 calibration may move, over which grid. | Yes |
| `protocols/` | Step-by-step human protocols: OD-1x, 5-race pilot, signal gate, hand-charting; `OPERATOR/` = keymap card, seeding walkthrough, anchor prompts. | Operational |
| `src/tripstate/` | Python package. M0 (ingest + video), M1 scaffold, M3 checks + seeding, M4 (tiering, cover, projection), M5 (states, smoothing, segments), M6 uncalibrated reference, M7 (gates, yield, shot gaps, runner QC), M8 (canonical export, SQLite store), evaluation, golden manifest, BORIS charting, text parse, signal gate, synthetic races, pilot stack; `release/` (freeze check, marker binding, promotion, DoD evaluation) and `calibration/` (§7.2 harness). | Code |
| `tests/` | Unit tests for the implemented logic and the freeze check. | Code |
| `tools/` | CLI helpers for the human protocols, spec hygiene, and the freeze → calibration → release path (`promote_draft.py`, `calibrate.py`, `evaluate_release.py`; each has a synthetic dry run). | Code |
| `docs/` | Architecture, risk register, glossary, per-module agent prompts. `docs/research/` = state-of-the-art notes with sources; `docs/STACK-2.0.md` = proposed default stack. | Informative |
| `data/` | Local data layout (gitignored). See `data/README.md`. | — |

## New session?

Read `docs/HANDOFF-NEXT-SESSION.md` first: reading order, green checks, the next block of work, owner-side items, phases.

## Current phase

See `STATUS.md` (live) and `ROADMAP.md` (phases P0–P6 with exit gates).

**Right now the project is in P1: cut the draft, then run OD-1x.** Nothing has
been measured on footage. Every camera and human-budget assumption is still
provisional.

## Prime directive

When uncertain, **FLAG AND DEGRADE, NEVER GUESS.** Applies to code, to charts,
and to this repository's documents: a number without evidence is marked `[EG]`,
not written as fact.

## Quick start

```bash
make setup          # install package + test deps
make test           # run unit tests
make synth-demo     # run a scripted synthetic race through M4→M5→M7→M8 and score it
make pilot-demo     # synthetic video → headless seeding → both pilot identity paths → kill-gate report
make freeze-check   # fails while any EG marker is un-instantiated (expected now)
make lint-spec      # table/ID hygiene on the spec files + draft reproducibility
make freeze-dry-run # rehearse the D-36 promotion on synthetic OD-1x sheets (temp dir, repo untouched)
make calibrate-dry-run  # §7.2 harness recovers a mis-set threshold on synthetic races
make evaluate-dry-run   # DoD-1…6 report on a synthetic M8 store
make od1x-rehearsal     # the owner's OD-1x afternoon rehearsed with synthetic inputs (temp dir)
```
