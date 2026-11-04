# Handoff — fresh session, start here

_Written 2026-11-04 at the end of the scaffolding session. Everything below is in this repository; nothing lives only in the old chat._

## 0. Read in this order (15 minutes)

1. `README.md` — repo map and the prime directive.
2. `STATUS.md` — what exists, what is blocked, what the owner still has to decide.
3. `CLAUDE.md` — rules for agents (spec version to cite, D-36 DRAFT rule, numbers are config, determinism, tests before acceptance).
4. `spec/SPEC-2.0.0-draft.md` — the governing spec (full prose, cut from 1.2.0 by `tools/cut_draft.py`; the ledger `spec/SPEC-2.0.0-draft-LEDGER.md` is the audit trail of every edit). Do not re-litigate D-01…D-25; D-26…D-36 are the agreed direction (`spec/decisions/DECISION-LOG.md`).
5. `spec/RECON-2.0.0-patches.md` — RP-1…RP-25: open proposals and findings; several need owner verdicts.
6. `docs/BACKLOG.md` — prioritized remaining work. A1–A3 and B1–B3 are done; **A5, A4, B6 are the next block** (this handoff).
7. `docs/AUDIT.md` and `docs/research/00-INDEX.md` — what was found and why things are the way they are.

Then run, in this order, and make sure all four are green before changing anything:

```bash
make setup          # pip install -e ".[dev]"  (ffmpeg must be installed; numpy, pyyaml, pytest, ruff)
make test           # 146 tests at handoff
make lint-spec      # table hygiene on both spec files + `tools/cut_draft.py --check` (draft must reproduce from the ledger script)
make freeze-check   # EXPECTED TO FAIL (exit 1): 16 evidence-gated values + 4 kill-gates are un-instantiated until OD-1x (D-36)
make synth-demo     # scripted synthetic race through M4→M5→M7→M8; mask IoU 1.0 against truth
make pilot-demo     # synthetic video → headless seeding with live flags → both identity paths → kill-gate report (dry run)
```

## 1. State of the project in one paragraph

The spec lineage is 1.0.0 → 1.2.0 (FROZEN, 2026-07-25) → **2.0.0-draft** (DRAFT, D-36). No footage has ever been inspected; OD-1x (the one-afternoon timed dry run on three replays) has not happened; the signal gate (does trip text carry edge over the market?) has not been run on the owner's corpus. Everything evidence-independent has been built and tested on synthetic data: M0 (metadata + ffmpeg video), M1 (shot segmenter scaffold), M3 (checks + live seeding loop), M4 (tiering, cover, projection, rail-based lateral options), M5 (states, smoothing, segments), M6 (uncalibrated reference detector), M7 (gates, yield, shot gaps, runner QC), M8 (canonical export, SQLite store), evaluation (§6.2 metrics, §6.4 audit), golden manifest, BORIS charting converter, text parser (§11), signal-gate harness, world-space simulator (track + pinhole camera), throwaway pilot stack with live flags, CLI, CI. The freeze → calibration → release path is the one part of the lifecycle with no tooling yet. That is the next block.

## 2. The next block: freeze-to-release tooling (A5, A4, B6)

Build in this order. Each item: what, where, acceptance, what NOT to do.

### A5 — `tools/promote_draft.py` + freeze dry run

**What.** One command that performs the D-36 promotion when `tools/freeze_check.py` exits 0:
1. refuse unless `freeze_check` passes (EG registry fully instantiated, KG-1…KG-4 `pass`; KG-5 advisory);
2. produce `spec/SPEC-2.0.0.md` from `spec/SPEC-2.0.0-draft.md`: Status → FROZEN, header promotion rule replaced by the freeze record (date, registry version, pilot evidence), every `` `[EG: …]` `` marker replaced by the instantiated value from `spec/registers/evidence_gated.yaml` (keep the provisional value in a footnote-style "(provisional was X)" only in the changelog row), `[OPEN: …]` markers must be resolved first (refuse if any remain, listing them);
3. append D-26…D-36 rows from `spec/decisions/DECISION-LOG.md` to §1 of the frozen file; move them from "Pending" to "Closed" in the decision log;
4. write the changelog row for 2.0.0 (template already in the draft's changelog);
5. write `config/thresholds/TS-2.0.0-frozen.yaml` from `TS-0.0.0-provisional.yaml` with EG values substituted, `eg: false`, `calibrated: false`, `search_provenance: "freeze"`;
6. bump `src/tripstate/version.py` (`SPEC_VERSION = "2.0.0"`, `SPEC_STATUS = "FROZEN"`) and `schema_version`;
7. keep `SPEC-2.0.0-draft.md`, the ledger and `cut_draft.py` as history (do not delete); add `tools/cut_draft.py --check` exemption once the frozen file exists (lint-spec should then check the frozen file too).
Also a **dry run**: `tools/promote_draft.py --dry-run --registry <path>` that simulates with a fully instantiated synthetic registry (use `tools/instantiate_eg.py` on the synthetic OD-1x sheets from `tests`/scratch: there is a sample in the tests for `instantiate_eg`; create `tests/fixtures/od1x_synthetic/` if needed) and a kill-gates file with all `pass`, writing outputs to a temp dir and diffing.
**Acceptance.** Tests: refuses on un-instantiated registry; refuses on remaining `[OPEN]`; dry run produces a frozen file with zero `[EG` markers, D-26…D-36 present in §1, changelog row present, `lint_spec.py` passes on it, `version.py` bumped only in the real run; the real run is idempotent (second run says "already frozen").
**Do not** run the real promotion. OD-1x has not happened.

### A4 — calibration harness (§7.2) — code only, never run for real before the freeze

**What.** `src/tripstate/calibration/`:
- `search.py`: grid search (Bayesian later) over a declared subset of threshold keys with ranges (YAML `config/calibration/search-space.yaml`, to create), objective = §6.2 headline score (`tripstate.evaluation.metrics.headline_score`) on **dev** charts only, constraints = both mask IoUs ≥ 0.85 (pre-calibration floors) and M6 candidate load ≤ 4 median; evaluate a candidate TS by re-running `chart_race` (M5) on stored M4 geometry (do not re-run M2/M3) — so the harness consumes `geometry` sidecars + hand charts;
- `tsio.py`: write `TS-x.y.yaml` with `search_provenance` (space, objective, best score, dev races, seed, date) and `calibrated: true`;
- `holdout.py`: one-shot held-out evaluation, writes a changelog row draft; implements the §7.2 rule "> 10 pt dev/held-out gap → spec revision, not more tuning";
- `tools/calibrate.py` CLI with a hard guard: refuses unless `tripstate.version.is_frozen()` and the golden manifest exists; `--synthetic` dry-run mode runs the whole loop on synthetic races (`tripstate.synth`) with a deliberately mis-set threshold and must recover it.
**Acceptance.** Synthetic dry run recovers a perturbed `cover_lat_sw` / `same_tier_sw` within one grid step; refuses on DRAFT; provenance round-trips through `ThresholdSet.load`.

### B6 — `tools/evaluate_release.py` (DoD-1…6)

**What.** From the M8 store + golden manifest: DoD-1 (both mask IoUs on held-out), DoD-2 (candidate recall point estimate + Wilson CI; invalid if < 10 held-out observable breaks), DoD-3 (median human-minutes over ≥ 20 eligible attempts incl. over_budget), DoD-4 (no unchartable rows in default views — query the store), DoD-5 (canonical SHA identity between two runs — accept two store paths), DoD-6 (≥ 8/10 held-out pass Q-1…Q-6); dual headline with and without Q-7 failures (D-35); per-stratum tables (day/night × field band × start_format × piste); writes `data/releases/<version>/evaluation.md` + a changelog row draft; `--synthetic` mode builds a store from synthetic races so the tool is testable now.
**Acceptance.** Synthetic mode produces the report with every DoD line and the right invalidity reasons when fixtures are undersized.

### After the block

Update `STATUS.md`, `docs/BACKLOG.md` (mark A4, A5, B6), `docs/ARCHITECTURE.md`, module READMEs, `docs/AUDIT.md` with anything found; commit with the attribution lines in CLAUDE.md's spirit (no model identifiers in commit messages); push.

## 3. Rules that bit us (keep them)

- **Exact-match patch scripts break after ruff's autofix re-sorts imports.** Re-read a file before patching it, or patch whole blocks.
- **`pytest | tail` hides the exit status.** Use `set -o pipefail` or run pytest last without a pipe before committing.
- **Synthetic fixtures must respect the closed cover interval `[0.3, 2.0]` SL** and the fact that adjacent-lane boxes touch at small render sizes.
- **`arxiv.org` and `docs.ultralytics.com` are unreachable from the cloud session**; cite from search summaries and mark unverified.
- **Never fake human-minutes:** headless seeding replays set `headless: true`; the pilot runner ignores their wall-clock unless `--human-minutes` is passed explicitly for dry runs.

## 4. Owner-side items (cannot be done by an agent)

| Item | Where | Unlocks |
|---|---|---|
| OD-1x afternoon on 3 replays | `protocols/OD-1x/PROTOCOL.md` + sheets; `tools/od1x_timer.py`; `tools/instantiate_eg.py` | every `[EG]` value, KG-1, KG-4, lateral-resolvability per track section (RP-24) |
| Signal gate on the real corpus | `protocols/SIGNAL-GATE/PROTOCOL.md`, `tools/signal_gate.py --corpus runners.csv` | KG-5: the go/no-go for the whole project |
| Decisions: RP-11, RP-12, RP-14/15/17, RP-18, RP-19 (refined), RP-21…RP-25, `events.saddle_no = 0`, `hand_charts` version columns | `spec/RECON-2.0.0-patches.md`, `STATUS.md` | M3 default stack, M4 lateral mode, §3.3 carve-out |
| LeTrot tracking pages (RP-6) | `docs/research/01-detection.md` | whether M2–M4 are needed at all for rank/position |
| Track plan / camera positions | `docs/research/11-simulated-geometry.md` | replaces the simulator's assumptions |

## 5. Phases after this block (feasible order)

1. **P2 OD-1x** (owner, one afternoon) → `instantiate_eg.py` → `freeze_check` → owner review of the draft and the RP verdicts.
2. **P3 signal gate** (owner, one evening) → KG-5.
3. **P4 pilot** on 5 real races: run `tools/seed_cli.py --engine sam2|detector` and `tools/pilot_run.py` with the real adapters (first time they run anywhere), `tools/pilot_report.py` → KG-2, KG-3, budget distribution.
4. **P5 freeze** with `tools/promote_draft.py` (this block).
5. **P6 golden charting** in BORIS (`protocols/HAND-CHARTING`), `tools/golden_manifest.py build`, M2 training (B5 scaffolding still open), calibration (`tools/calibrate.py`), release evaluation (`tools/evaluate_release.py`).
6. Remaining backlog: C1 metadata ingest adapter, C2 corpus registry, C3 env fingerprint, C4 compute plan/benchmark, C6 OD-1x rehearsal target, C7 operator card, D1 decision memos, D2 invariant tests, B4 M8 sidecars/export views, B5 M2 training scaffolding.

## 6. Prompt to start the fresh session

```
Repository: sznajdr/vddd (clone it; this is the Vincennes attelé trip-state project).
Read docs/HANDOFF-NEXT-SESSION.md first and follow its reading order, then run make test, make lint-spec, make freeze-check (expected to fail), make synth-demo.
Then build the freeze-to-release tooling exactly as §2 of the handoff specifies, in order: A5 (tools/promote_draft.py + freeze dry run), A4 (calibration harness, code only, synthetic dry run), B6 (tools/evaluate_release.py).
Rules: cite SPEC-2.0.0-draft; numbers are config (D-18); never run the real promotion or calibration (D-36, OD-1x has not happened); tests before acceptance; commit on green only (no pipes hiding pytest's exit status); no model identifiers in commits.
When done: update STATUS.md, docs/BACKLOG.md, docs/ARCHITECTURE.md, docs/AUDIT.md; push; report what was built, what was found, what the owner must decide, and the next feasible phases.
```
