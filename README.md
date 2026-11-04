# Vincennes Attelé Trip-State Extraction — project repository

Extract per-horse **trip-state charts** (cover, width tier, position rank, breaks) from Equidia broadcast replays of Vincennes trot attelé races, as overlay features for a downstream prediction model.

The governing document is the spec in `spec/`. Everything else in this repository exists to (a) freeze that spec on evidence instead of assumption, and (b) build the pipeline against it once frozen. **Nothing here has seen a frame of real video**: every module is a tested reference implementation on synthetic data, and every owner-side step has a rehearsal.

## Where things are

| Path | What it is | Normative? |
|---|---|---|
| `spec/` | `SPEC-2.0.0-draft.md` (DRAFT, generated from 1.2.0 + the ledger by `tools/cut_draft.py`), the ledger, the decision log, the evidence-gated and kill-gate registers. Index: `spec/README.md`. | Yes |
| `config/thresholds/` | Versioned threshold sets (`TS-x.y.z.yaml`); every numeric cutoff lives here (D-18), including the DoD floors (`release`) and §7.2 constraints (`calibration`). `config/calibration/search-space.yaml` declares what calibration may move. | Yes |
| `protocols/` | What the owner does with a stopwatch and a notebook: OD-1x, pilot, signal gate, hand-charting, operator card. Index: `protocols/README.md`. | Operational |
| `src/tripstate/` | The Python package, M0…M8 plus evaluation, golden manifest, charting, text parse, signal gate, synthetic races, pilot stack, calibration and release tooling. Map: `src/tripstate/README.md`. | Code |
| `tools/` | Command-line entry points over the package; each says whether it runs today or needs real inputs. Catalogue: `tools/README.md`. | Code |
| `tests/` | Unit, acceptance and property tests; `tests/fixtures/od1x_synthetic/` is the freeze rehearsal fixture (not evidence). | Code |
| `docs/` | Handoff, architecture, backlog, audit log, risk register, glossary, stack, decisions, research pack. Index: `docs/README.md`. | Informative |
| `data/` | Local data layout (gitignored). See `data/README.md`. | — |
| `STATUS.md`, `ROADMAP.md`, `CLAUDE.md` | live board; phases P0–P6 with exit gates; rules for coding agents | — |

## Where the project stands

Spec lineage 1.0.0 → 1.2.0 (FROZEN) → **2.0.0-draft** (DRAFT, D-36). Phase P1 is complete and the delegated design decisions are applied (ledger L-46…L-51). The next steps are owner-side: **P2 OD-1x** (one afternoon on three replays), **P3 the signal gate** (one evening on the owner's corpus), **P4 the five-race pilot**. Those instantiate the registers; then `tools/freeze_check.py` passes, `tools/promote_draft.py` freezes 2.0.0 in one commit, and golden charting, calibration (`tools/calibrate.py`) and the release evaluation (`tools/evaluate_release.py`) become allowed. See `STATUS.md` for blockers and `ROADMAP.md` for the gates.

## Quick start

```bash
make setup          # pip install -e ".[dev]"   (ffmpeg must be installed; numpy, pyyaml, pytest, ruff, hypothesis)
make check          # ruff + both spec lints + docs lint + tests (what CI runs; pytest last, unpiped)
make freeze-check   # EXPECTED TO FAIL until OD-1x and the pilot (D-36)
make dry-runs       # the four rehearsals: freeze promotion, calibration, release evaluation, OD-1x afternoon
make synth-demo     # a scripted synthetic race through M4→M5→M7→M8
make pilot-demo     # synthetic video → headless seeding → both pilot identity paths → kill-gate report
make help           # every target
```

## Prime directive

When uncertain, **FLAG AND DEGRADE, NEVER GUESS.** Applies to code, to charts, and to this repository's documents: a number without evidence is marked `[EG]`, not written as fact; a dry run writes to a temp dir and marks its rows synthetic; a tool that cannot decide returns the abstention value and a reason.

## New session?

Read `docs/HANDOFF-NEXT-SESSION.md` first: reading order, green checks, the next executable queue, owner-side items, phases.
