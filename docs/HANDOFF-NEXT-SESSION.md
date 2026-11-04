# Handoff — fresh session, start here

_Written 2026-11-04 at the end of the freeze-to-release tooling session (A5, A4, B6). Everything below is in this repository; nothing lives only in the old chat._

## 0. Read in this order (15 minutes)

1. `README.md` — repo map and the prime directive.
2. `STATUS.md` — what exists, what is blocked, what the owner still has to decide (six open questions now).
3. `CLAUDE.md` — rules for agents (spec version to cite, D-36 DRAFT rule, numbers are config, determinism, tests before acceptance).
4. `spec/SPEC-2.0.0-draft.md` — the governing spec (full prose, cut from 1.2.0 by `tools/cut_draft.py`; the ledger `spec/SPEC-2.0.0-draft-LEDGER.md` is the audit trail of every edit). Do not re-litigate D-01…D-25; D-26…D-36 are the agreed direction (`spec/decisions/DECISION-LOG.md`).
5. `spec/RECON-2.0.0-patches.md` — RP-1…RP-25: open proposals and findings; several need owner verdicts.
6. `docs/BACKLOG.md` — prioritized remaining work. A1–A5 and B1–B3, B6 are done; **the next block is C-series de-risking of the owner's first real day** (§2 below).
7. `docs/ARCHITECTURE.md` (incl. the new "Freeze → calibration → release" section), `docs/AUDIT.md` and `docs/research/00-INDEX.md` — what was found and why things are the way they are.

Then run, in this order, and make sure everything is green (except `freeze-check`, which must fail) before changing anything:

```bash
make setup              # pip install -e ".[dev]"  (ffmpeg must be installed; numpy, pyyaml, pytest, ruff)
make lint               # ruff
make test               # 170 tests at handoff
make lint-spec          # table hygiene on both spec files + `tools/cut_draft.py --check` (+ the frozen file once it exists)
make freeze-check       # EXPECTED TO FAIL (exit 1): 19 EG entries, 4 kill-gates, 2 unbound markers, 3 open owner decisions
make synth-demo         # scripted synthetic race through M4→M5→M7→M8; mask IoU 1.0 against truth
make freeze-dry-run     # synthetic OD-1x sheets + pilot reports → instantiated registry → simulated promotion in /tmp (diffs, lint OK)
make calibrate-dry-run  # §7.2 harness recovers a deliberately mis-set cover_lat_sw / same_tier_sw exactly
make evaluate-dry-run   # DoD-1…6 report on a synthetic M8 store (every line `pass`; undersized fixtures → `invalid` in the tests)
make pilot-demo         # synthetic video → headless seeding with live flags → both identity paths → kill-gate report (dry run)
```

## 1. State of the project in one paragraph

The spec lineage is 1.0.0 → 1.2.0 (FROZEN, 2026-07-25) → **2.0.0-draft** (DRAFT, D-36). No footage has ever been inspected; OD-1x has not happened; the signal gate has not been run on the owner's corpus. Everything evidence-independent has been built and tested on synthetic data: M0–M8 reference implementations, evaluation, golden manifest, BORIS converter, text parser, signal-gate harness, world-space simulator, throwaway pilot stack, CLI, CI — and now the complete freeze → calibration → release path: `tools/freeze_check.py` (binds every `[EG]` marker), `tools/instantiate_eg.py` (sheets + pilot reports), `tools/promote_draft.py` (the D-36 promotion, dry run and an isolated-copy real-run rehearsal), `tools/calibrate.py` (§7.2 harness, refused while DRAFT), `tools/evaluate_release.py` (DoD-1…6). None of these has run for real. The project is waiting on the owner: OD-1x, the signal gate, the pilot, and six decisions (`STATUS.md`).

## 2. The next block: de-risk the owner's first real day (C3, C6, C7, C8, D1, D2)

Build in this order. Each item: what, where, acceptance, what NOT to do.

### C6 — `make od1x-rehearsal`
**What.** One target that chains `tools/synth_video.py` (a clip), `tools/od1x_timer.py` (stopwatch → `sheet_seeding.csv`), the six sheet templates copied to a temp `data/od1x/`, and `tools/instantiate_eg.py --dry-run` on them, printing what the owner will see. Reuse `tests/fixtures/od1x_synthetic/` for the filled-sheet example (`make freeze-dry-run` already covers sheets → registry → promotion).
**Acceptance.** Runs green from a clean checkout; the printed proposals match `tests/test_promote_draft.py::test_instantiate_from_synthetic_sheets_and_pilot`.
**Do not** add new EG keys or change instantiation rules.

### C8 — calibration input exporter
**What.** `tools/export_calibration_inputs.py --store … --manifest … --out data/calibration/`: writes `<race_id>.geometry.json` (`RaceGeometry.from_projector` needs the pipeline's `FrameGeometry` list — persist it from the pipeline run; until B4 lands, accept a JSON dump of frames) and `<race_id>.hand_chart.json` from the `hand_charts` table, checking S-6 (`split` vs manifest).
**Acceptance.** `tools/calibrate.py` consumes the exported directory in a test built from `tripstate.release.synthetic_store` (which already writes hand charts); the real run still refuses while DRAFT.

### C3 — environment fingerprint
**What.** `tools/env_fingerprint.py` → `versions.determinism_env` JSON (python/numpy/torch/CUDA/cuDNN/driver/GPU when present, `use_deterministic_algorithms`, TF32 flags, seeds, weight hashes); `requirements-cv.txt` pinned. Store it via `Store.insert("versions", …)`.
**Acceptance.** Deterministic output on the same machine; absent libraries recorded as `null`, never guessed.

### C7 — operator material
**What.** One-page keymap card from `SeedingSession`'s keymap, 10-minute seeding walkthrough, EC-04 anchor prompts per start type (`protocols/`).
**Acceptance.** Every key in the card exists in `tripstate.seeding.session`; a test parses the card and checks it.

### D1 — decision memos
**What.** `docs/decisions/` one page each, options + recommendation, ready to sign: RP-11, RP-12, RP-14/15/17, RP-18, RP-19 (refined)/RP-22/RP-23/RP-24/RP-25, `events.saddle_no = 0`, `hand_charts` version columns, **`stratum_yield_review_factor`** (STATUS question 5), the §5.1 heading marker (AUDIT open item). Each memo ends with the exact ledger edit (`tools/cut_draft.py` `rep(...)` call) that implements the recommendation, so resolving an `[OPEN]` marker is a copy-paste.
**Do not** apply the edits: the verdicts are the owner's.

### D2 — spec invariant tests
**What.** Property-based tests (hypothesis, add to dev deps) on `chart_race`: exactly one base segment per instant, overlays inside visibility, half-open intervals, at most one lead per frame; determinism of `ordinal_ids` / canonical export under row shuffling; marker binding stable under ledger edits that do not touch markers.

### After the block
Update `STATUS.md`, `docs/BACKLOG.md`, `docs/ARCHITECTURE.md`, module READMEs, `docs/AUDIT.md`; commit (no model identifiers in commit messages); push.

## 3. Rules that bit us (keep them)

- **Exact-match patch scripts break after ruff's autofix re-sorts imports.** Re-read a file before patching it, or patch whole blocks.
- **`pytest | tail` hides the exit status.** Use `set -o pipefail` or run pytest last without a pipe before committing.
- **Synthetic fixtures must respect the closed cover interval `[0.3, 2.0]` SL**, keep every offset ≥ 0.05 away from a threshold (floating-point boundaries flip per frame), and remember that adjacent-lane boxes touch at small render sizes.
- **`load_default()` changes meaning at the freeze** (it returns `TS-2.0.0-frozen.yaml` once `version.py` says FROZEN): tools that reason about *provisional* flags must load `TS-0.0.0-provisional.yaml` explicitly (`lint_spec.py` does now).
- **The draft is reproduced from the ledger** (`tools/cut_draft.py --check` in CI): never edit `spec/SPEC-2.0.0-draft.md` by hand; add a ledger row and a `rep(...)` edit.
- **`arxiv.org` and `docs.ultralytics.com` are unreachable from the cloud session**; cite from search summaries and mark unverified.
- **Never fake human-minutes:** headless seeding replays set `headless: true`; the pilot runner ignores their wall-clock unless `--human-minutes` is passed explicitly for dry runs.

## 4. Owner-side items (cannot be done by an agent)

| Item | Where | Unlocks |
|---|---|---|
| OD-1x afternoon on 3 replays | `protocols/OD-1x/PROTOCOL.md` + sheets; `tools/od1x_timer.py`; `tools/instantiate_eg.py` (now also `normalized_fps`, `sw_ratio`, and `--pilot-reports` for the D-29 keys) | every `[EG]` value, KG-1, KG-4, lateral-resolvability per track section (RP-24) |
| Signal gate on the real corpus | `protocols/SIGNAL-GATE/PROTOCOL.md`, `tools/signal_gate.py --corpus runners.csv` | KG-5: the go/no-go for the whole project |
| Decisions: RP-11, RP-12, RP-14/15/17, RP-18, RP-19 (refined), RP-21…RP-25, `events.saddle_no = 0`, `hand_charts` version columns, **`stratum_yield_review_factor` (marker without instrument)**, the three `[OPEN]` markers (ledger edits) | `spec/RECON-2.0.0-patches.md`, `STATUS.md` questions 5–6, `docs/AUDIT.md` | M3 default stack, M4 lateral mode, §3.3 carve-out, **and the promotion itself (`promote_draft.py` refuses while any `[OPEN]` or unbound marker remains)** |
| LeTrot tracking pages (RP-6) | `docs/research/01-detection.md` | whether M2–M4 are needed at all for rank/position |
| Track plan / camera positions | `docs/research/11-simulated-geometry.md` | replaces the simulator's assumptions; `track_width_sl` |

## 5. Phases after this block (feasible order)

1. **P2 OD-1x** (owner, one afternoon) → `instantiate_eg.py data/od1x --out spec/registers/evidence_gated.yaml` → `freeze_check` → owner review of the draft and the RP verdicts (ledger edits resolve the `[OPEN]` markers; `cut_draft.py --check` stays green).
2. **P3 signal gate** (owner, one evening) → KG-5.
3. **P4 pilot** on 5 real races: `tools/seed_cli.py --engine sam2|detector`, `tools/pilot_run.py` with the real adapters (first time they run anywhere), `tools/pilot_report.py --kill-gates spec/registers/kill_gates.yaml` → KG-2, KG-3; `instantiate_eg.py --pilot-reports` → D-29 keys.
4. **P5 freeze:** `tools/freeze_check.py` exit 0 → `tools/promote_draft.py` (one commit: frozen spec, frozen TS, decision log, `version.py`) → `make test lint-spec freeze-check`.
5. **P6 golden charting** in BORIS (`protocols/HAND-CHARTING`), `tools/golden_manifest.py build`, M2 training (B5 scaffolding still open), pipeline runs → `data/calibration/` (C8) → `tools/calibrate.py` (dev, then `--heldout` once) → `tools/evaluate_release.py --store … --store2 …` → `data/releases/<version>/evaluation.md`, changelog row appended to §14.
6. Remaining backlog: C1 metadata ingest adapter, C2 corpus registry, C4 compute plan/benchmark, C5 corpus dashboard, C9 changelog appender, B4 M8 sidecars/export views, B5 M2 training scaffolding, D3/D4 hygiene.

## 6. Prompt to start the fresh session

```
Repository: sznajdr/vddd (clone it; this is the Vincennes attelé trip-state project).
Read docs/HANDOFF-NEXT-SESSION.md first and follow its reading order, then run make lint, make test, make lint-spec,
make freeze-check (expected to fail), make synth-demo, make freeze-dry-run, make calibrate-dry-run, make evaluate-dry-run.
Then build the owner-day de-risking block exactly as §2 of the handoff specifies, in order: C6 (make od1x-rehearsal),
C8 (calibration input exporter), C3 (env fingerprint), C7 (operator material), D1 (decision memos incl. the exact ledger edits),
D2 (spec invariant tests).
Rules: cite SPEC-2.0.0-draft; numbers are config (D-18); never edit the draft by hand (ledger + cut_draft.py); never run the real
promotion or calibration (D-36, OD-1x has not happened); tests before acceptance; commit on green only (no pipes hiding pytest's
exit status); no model identifiers in commits.
When done: update STATUS.md, docs/BACKLOG.md, docs/ARCHITECTURE.md, docs/AUDIT.md; push; report what was built, what was found,
what the owner must decide, and the next feasible phases.
```
