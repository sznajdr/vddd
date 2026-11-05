# Handoff — fresh session, start here

_Updated 2026-11-05 for integration of PR #1 after the continuation queue (C6, C8, C3, C7, RP-18, D2) and documentation pass. Governing version: SPEC-2.0.0-draft. For subsequent work, fetch current `main` and create a new feature branch; do not resume the completed PR #1 branch. Preserve concurrent commits._

## 0. Read in this order (15 minutes)

1. `README.md` — repo map, where the project stands, the prime directive.
2. `STATUS.md` — what exists, what blocks the freeze (evidence only), what was decided.
3. `CLAUDE.md` — the twelve rules (spec version, D-36, numbers are config, generated draft, green before commit, honest map).
4. `spec/README.md` → `spec/SPEC-2.0.0-draft.md` — the governing spec; `docs/decisions/2026-11-04-continuation.md` for the settled design verdicts (ledger L-46…L-51).
5. `docs/README.md` → `docs/ARCHITECTURE.md`, `docs/BACKLOG.md`, `docs/AUDIT.md`.
6. `tools/README.md` and `protocols/README.md` — what runs today and what the owner does.

Then run, and make sure everything is green except `freeze-check`, which must fail:

```bash
make setup          # pip install -e ".[dev]"  (ffmpeg must be installed)
make check          # ruff + both spec lints + docs lint + 194 tests (pytest last, unpiped)
make freeze-check   # EXPECTED TO FAIL (exit 1): 19 EG entries + KG-1…KG-4 await OD-1x and the pilot
make dry-runs       # freeze promotion, calibration, release evaluation, OD-1x afternoon — all on synthetic inputs
make pilot-demo     # synthetic video → headless seeding → both identity paths → kill-gate report
```

## 1. State of the project in one paragraph

Spec lineage 1.0.0 → 1.2.0 (FROZEN) → **2.0.0-draft** (DRAFT, D-36). No footage has ever been inspected; OD-1x, the signal gate and the pilot have not happened. Everything evidence-independent is built and tested on synthetic data: M0–M8 reference implementations, evaluation, golden manifest, BORIS converter, text parser, signal-gate harness, simulator, throwaway pilot stack, seeding loop, and the complete freeze → calibration → release path with rehearsals (`make dry-runs`). The delegated design queue is settled and applied (L-46…L-51, incl. RP-18 seed provenance). Documentation is indexed and linted (`make lint-docs`). The draft has zero open decisions and zero unbound markers; the only freeze blockers are real measurements.

## 2. The next block — execute in this order

Each item: what, acceptance, what NOT to do. Push after each coherent block; update `STATUS.md`, `docs/BACKLOG.md`, module READMEs and `tools/README.md` (the docs lint will remind you).

### B4 — M8 sidecars, export views, migration procedure
**What.** (i) Frame-level sidecars: the per-race frame record (`tripstate.m4_geometry.frames_to_json`) and the calibration sidecar (`tripstate.calibration.sidecar`) written by a pipeline run under `data/frames/` / `data/store/sidecars/`, as parquet when `pyarrow` is importable and JSON otherwise, with their SHA-256 recorded in the store (`tracklets.boxes_sidecar_sha256` exists; add a `geometry_sidecar_sha256` column to `qc` or a small `sidecars` table — additive, via `Store.migrate_additive()`, with a ledger row for §9); (ii) feature-export views: the fixed race-fraction *calls* view (research 09: state per runner at declared fractions) next to `v_state_segments_chartable`, chartable-only, no override parameter; (iii) the migration procedure documented in `src/tripstate/m8_storage/README.md` with a test that opens a store built from an older DDL.
**Acceptance.** Round trip of a synthetic race through the store with sidecar hashes in the canonical payload; the calls view is byte-identical across two runs; `tools/export_calibration_inputs.py` consumes a sidecar the store points to.
**Do not** change any primary key or make a column NOT NULL (breaking = major).

### B5 — M2 training scaffolding (synthetic references only)
**What.** `src/tripstate/m2_detect/training.py` + `tools/m2_dataset.py`: COCO export from CVAT-style keyframe labels, race-disjoint split enforced from the golden manifest (detector holdout ≠ system holdout, §6.1), Ultralytics / RF-DETR config templates carrying the D-32 determinism knobs (from `tripstate.m8_storage.determinism`), an evaluator for AP@0.5 and per-frame recall by field size and stratum. Everything tested on synthetic COCO files; no model is trained.
**Acceptance.** A synthetic dataset built from `tripstate.synth` boxes round-trips through export → split → evaluator with a perfect oracle "detector" scoring 1.0 and a degraded one scoring below the floors.
**Do not** train anything or download weights; the real adapters stay lazy imports.

### C9 — changelog appender
**What.** `tools/changelog_append.py ROW.md --spec spec/SPEC-2.0.0.md`: inserts the row drafts written by `calibrate.py --heldout` and `evaluate_release.py` into §14 (after the latest row of the same version), refusing a draft file (`SPEC_STATUS = DRAFT`) and a malformed row (column count). Test on a copy of the draft promoted in a temp dir (see `tests/test_promote_draft.py::test_real_run_on_an_isolated_copy_is_idempotent_and_consistent` for the recipe).

### D4 — release alignment
**What.** `tripstate.__version__` derived from `SPEC_VERSION`; `pyproject.toml` version follows (`2.0.0.dev0` while DRAFT); `tools/promote_draft.py` bumps it in the same commit; a test pins the three in step.

### D3 — type checking and docs build
**What.** `mypy` (or pyright) config with the package passing at a declared strictness, `make typecheck` in `make check`; API docs from docstrings only if a zero-dependency route exists (otherwise skip and say so).

### C4 / C5 — compute plan and corpus dashboard
**What.** `docs/COMPUTE-PLAN.md` with the arithmetic (600 races × ~3 min × 25 fps ≈ 2.7 M frames; cost per backend) and `tools/bench.py` measuring frames/s per backend (numbers only when run on the owner's machine; the tool prints "not measured" otherwise); `tools/corpus_status.py` over the store: races by stage, failure-code histogram, per-stratum yield (D-35) — tested on the synthetic store.

## 3. Rules that bit us (keep them)

- **The draft is generated.** Never edit `spec/SPEC-2.0.0-draft.md`; ledger row + `rep(...)` in `tools/cut_draft.py`, regenerate, `--check` stays green.
- **`pytest | tail` hides the exit status.** `make check` runs pytest last and unpiped.
- **Exact-match patch scripts break after ruff's autofix.** Re-read a file before patching it; assert exactly one match.
- **Synthetic fixtures:** respect the closed cover interval `[0.3, 2.0]` SL; keep every offset ≥ 0.05 away from a threshold (floating-point boundaries flip per frame); the scripted race's lanes sit exactly 1 SW apart, so it cannot discriminate `cover_lat_sw` (use `tripstate.calibration.synthetic` for that).
- **`load_default()` changes meaning at the freeze** (it returns `TS-2.0.0-frozen.yaml` once `version.py` says FROZEN): code that reasons about provisional flags loads `TS-0.0.0-provisional.yaml` explicitly.
- **The uncalibrated M6 reference overshoots the §7.2 load cap on the scripted race**; the harness reports infeasibility rather than hiding it.
- **Never fake human-minutes:** headless replays set `headless: true`; the pilot runner ignores their wall-clock unless `--human-minutes` is passed explicitly for dry runs; scripted stopwatch rows are refused for non-`SYNTH-` race ids.
- **`arxiv.org` and `docs.ultralytics.com` are unreachable from the cloud session**; cite from search summaries and mark unverified.

## 4. Owner-side items (cannot be done by an agent)

| Item | Where | Unlocks |
|---|---|---|
| OD-1x afternoon on 3 replays | `protocols/OD-1x/PROTOCOL.md`; rehearse with `make od1x-rehearsal`; `tools/od1x_timer.py`; `tools/instantiate_eg.py` | every `[EG]` value, KG-1, KG-4 |
| Signal gate on the real corpus | `protocols/SIGNAL-GATE/PROTOCOL.md`, `tools/signal_gate.py --corpus runners.csv` | KG-5: the go/no-go for the whole project |
| 5-race pilot | `protocols/PILOT-5/PROTOCOL.md`, `protocols/OPERATOR/`, `tools/seed_cli.py`, `tools/pilot_run.py`, `tools/pilot_report.py --kill-gates`, `tools/instantiate_eg.py --pilot-reports` | KG-2, KG-3, D-29 budget keys |
| Replay paths, notule corpus, metadata schema | `data/README.md`; backlog C1/C2 | everything above; the ingest adapter |
| Track plan / camera positions (optional) | `docs/research/11-simulated-geometry.md` | `track_width_sl`, replaces simulator assumptions |

## 5. Phases after this block

1. **P2 OD-1x** → `instantiate_eg.py data/od1x --out spec/registers/evidence_gated.yaml` → `freeze_check`.
2. **P3 signal gate** → KG-5.
3. **P4 pilot** → `pilot_report.py --kill-gates` → KG-2/KG-3; `instantiate_eg.py --pilot-reports` → D-29 keys.
4. **P5 freeze:** `freeze_check.py` exit 0 → `promote_draft.py` (one commit) → `make check`.
5. **P6:** `golden_manifest.py build` → BORIS charting → pipeline runs → `export_calibration_inputs.py` → `calibrate.py` (dev, then `--heldout` once) → `evaluate_release.py --store … --store2 …` → `changelog_append.py`.

## 6. Prompt to start the fresh session

```
Repository: sznajdr/vddd (clone it; this is the Vincennes attelé trip-state project). Fetch current main and create a new feature branch for the next block. PR #1 delivered the prior block; do not resume its branch.
Read docs/HANDOFF-NEXT-SESSION.md first and follow its reading order, then run make check, make freeze-check (expected to fail), make dry-runs, make pilot-demo.
Then build the next block exactly as §2 of the handoff specifies, in order: B4 (M8 sidecars, export views, migration), B5 (M2 training scaffolding on synthetic data), C9 (changelog appender), D4 (release alignment), D3 (type checking), C4/C5 (compute plan, corpus dashboard).
Rules: cite SPEC-2.0.0-draft; numbers are config (D-18); never edit the generated draft by hand (ledger + tools/cut_draft.py); never run the real promotion, calibration, charting or training (D-36); tests before acceptance; make check green before every commit (pytest last, unpiped); no model identifiers in commits; keep tools/README.md, package READMEs and STATUS.md current (make lint-docs).
When done: update STATUS.md, docs/BACKLOG.md, docs/ARCHITECTURE.md, docs/AUDIT.md; push; report what was built, what was found, what the owner must decide, and the next feasible phases.
```
