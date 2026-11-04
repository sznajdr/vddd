# Backlog — what can still be prepared, researched or outlined before footage exists

Status 2026-11-04. Everything below is doable in this repository without replays unless marked **owner** (needs the owner's data or a decision) or **footage** (needs real video). Effort: S = hours, M = a day, L = several days of agent time. "Unlocks" says why it matters.

## A. Highest leverage (turn predictions into measurements, or gate the project)

| # | Item | Why / unlocks | Needs | Effort |
|---|---|---|---|---|
| A1 ✅ | **Perspective camera + bends in the synthetic simulator** — done 2026-11-04, see `docs/research/11-simulated-geometry.md` and RP-19…RP-25. Replace the affine render with a pinhole camera (yaw, pitch, focal length) and a curved track (Vincennes-like radii), then measure lateral compression (RP-5), bend-induced axis error (RP-20) and axis-accuracy sensitivity (RP-21) numerically. | Converts three open geometric risks from reasoning into simulated numbers; lets the `sw_ratio` per-shot aid (RP-19) and `axis_neighbourhood_k` be designed and tested before OD-1x. Still a model, but a quantitative one. | — | M |
| A2 ✅ | **Signal-gate harness** — done 2026-11-04 (`tripstate.signal`, `tools/signal_gate.py`, `decision.yaml`). `tripstate/signal/`: features from prior-race notule phrases (§11.2 families), market baseline from odds, time-ordered folds, L2 logistic regression in numpy, log-loss / AUC / Wilson CIs, the pre-registered decision rule from `protocols/SIGNAL-GATE`. Tested on synthetic corpora; runs on the owner's CSV the day it is pointed at it. | The project's go/no-go (KG-5, R-1) becomes a one-command run instead of an evening of ad-hoc analysis. | owner data to run; code now | M |
| A3 ✅ | **Text-parse skeleton (§11)** — done 2026-11-04 (`tripstate.textparse`, `tools/parse_notules.py`, `tools/lexicon_attest.py`). Vocabulary table loader from §11.2, `[C]`/`[P]` evidence flags, subject binding, negation / comparison / third-party scope, candidate sets instead of best guess, `phase` from §11.4, `hand_charts`-shaped output with the schema-additive columns. Tests on synthetic French sentences. | Feeds A2 directly; is the parallel workstream §12 names; makes `text_parse` charts available before any CV. | owner corpus to validate | M |
| A4 | **Calibration harness (§7.2).** Search over the threshold registry against dev charts (grid now, Bayesian later), objective = headline score, constraints = mask floors + candidate load; writes `TS-x.y.yaml` with search provenance; one-shot held-out report with the > 10 pt gap rule. Tested on synthetic charts with a deliberately mis-set threshold. | The freeze → calibration step becomes mechanical and auditable. MUST NOT be run for real before the freeze (D-36); the code can exist. | — | M |
| A5 | **Promotion script (`tools/promote_draft.py`) + freeze dry run.** Rename to FROZEN, append D-26…D-36 to §1, strip `[EG]` markers using the instantiated registry, write the changelog row, bump `version.py`; rehearse with synthetic OD-1x sheets end to end. | One-command freeze; verifies the whole D-36 mechanics before it matters. | — | S |

## B. Module stubs that can be filled on synthetic data

| # | Item | Why / unlocks | Needs | Effort |
|---|---|---|---|---|
| B1 | **M1 shot segmenter scaffold.** Pluggable boundary detector (numpy histogram/pixel-difference cut detector now; TransNetV2 adapter lazy), shot-type classifier interface (CLIP prompt-ensemble adapter lazy; heuristic for synthetic), static-region overlay mask (numpy), `replay_insert` heuristics, contiguity invariant, acceptance evaluator (boundary F1 ± 0.5 s, type accuracy, mask F1). Extend the renderer with cuts, a lower-third banner and a slow-motion insert. | Removes the last fully-stubbed module; produces the `SHOT_GAP` inputs M7 already consumes. | — | M |
| B2 | **M3 finish / start checks.** Crossing reconstruction against a finish-line segment in pixel space, reference-order comparison with the D-23 carve-out, D-25/D-30 ladder incl. `finish_evidence_min_k`, the relegation and zero-crossing fixtures; autostart two-row and volte band start checks (DR-04). All on synthetic geometry. | Completes M3 logic; the two synthetic fixtures the draft names become real tests. | — | M |
| B3 | **M7 runner QC.** `pct_time_visible`, final-third fractions, occlusion counts, EC-03 terminal handling and `terminal_before_final_third`, denominators per runner; `qc.realization` tagging. | Finishes M7; needed by D-11's "features MUST consume visible and stateable fractions". | — | S |
| B4 | **M8 sidecars, export views, migrations.** Frame-level series sidecars (npz now, parquet when pyarrow is installed) with SHA-256 in the canonical payload; feature-export views incl. the fixed race-fraction *calls* view (research 09); schema-version migration procedure + script. | Closes M8's DoD; gives downstream a stable export. | — | S |
| B5 | **M2 training scaffolding.** COCO export from CVAT, race-disjoint split enforced from the golden manifest, Ultralytics / RF-DETR config templates with the determinism knobs, evaluator (AP@0.5, per-frame recall by field size and stratum). Tested on synthetic COCO files. | Day-one readiness for M2 once frames are labelled. | footage to train | S |
| B6 | **DoD evaluation runner.** `tools/evaluate_release.py`: DoD-1…6 from store + manifest, dual headline (with/without Q-7), Wilson CI, per-stratum tables, changelog entry draft. | Makes a release evaluation reproducible and reviewable. | — | S |

## C. Data, operations, environment

| # | Item | Why / unlocks | Needs | Effort |
|---|---|---|---|---|
| C1 | **Metadata ingest adapter.** Column-mapping config from the owner's Equidia/LeTrot corpus schema to the M0 input contract (`piste`, `autostart_row`, revision evidence, raw time strings); validator reporting missing fields per race. | The 90,451-row corpus becomes `races`/`runners` rows with one config file. | owner schema | S |
| C2 | **Corpus registry + candidate pool.** Eligible races (Vincennes, attelé, ≤ 14), strata counts, boring/break expectations from notules, candidate CSV for `golden_manifest.py`. | Golden selection is ready the day of the freeze. | owner data | S |
| C3 | **Environment fingerprint.** `tools/env_fingerprint.py` → `versions.determinism_env` JSON (torch/CUDA/cuDNN/driver/GPU, flags, seeds, weight hashes); pinned `requirements-cv.txt`. | D-32 evidence; reproducible pilot. | — | S |
| C4 | **Compute plan + benchmark.** `docs/COMPUTE-PLAN.md` with the arithmetic (600 races × ~3 min × 25 fps ≈ 2.7 M frames; cost per backend) and `tools/bench.py` measuring frames/s of each backend on the owner's machine. | Answers R-15 (SAM throughput at 14 objects) with a number instead of a worry. | owner hardware to run | S |
| C5 | **Corpus status dashboard.** `tools/corpus_status.py`: races by stage (ingested, seeded, charted, chartable), failure-code histogram, per-stratum yield (D-35) from the store. | Operations visibility; the D-35 review trigger becomes a report line. | — | S |
| C6 | **OD-1x rehearsal target.** `make od1x-rehearsal`: synthetic clip + timer + sheets + `instantiate_eg.py` dry run, so the owner's afternoon has no tooling surprises. | De-risks the single most important owner day. | — | S |
| C7 | **Operator material.** One-page keymap card, 10-minute seeding walkthrough, EC-04 anchor prompts per start type. | Faster DoD-3 numbers; fewer protocol errors. | — | S |

## D. Spec, governance, quality

| # | Item | Why / unlocks | Needs | Effort |
|---|---|---|---|---|
| D1 | **Decision memos for the pending queue.** One page each, options + recommendation, ready to sign: RP-11 (table gap), RP-12 (M3 default), RP-14/15/17 (metrics, M1 stack, BORIS), RP-18 (seed pixel columns), RP-19/20/21 (geometry), `events.saddle_no = 0`, `hand_charts` version columns. | Turns a scattered list into ten short reads for the owner. | owner verdicts | S |
| D2 | **Spec invariant tests.** Property-based tests (hypothesis) on `chart_race`: exactly one base segment per instant, overlays inside visibility, half-open intervals, at most one lead per frame, determinism of `ordinal_ids`/canonical export under row shuffling. | Catches regressions in the normative rules independent of fixtures. | — | S |
| D3 | **Type checking and docs build.** mypy/pyright config, `make check`, API docs from docstrings. | Hygiene for agent hand-offs. | — | S |
| D4 | **Release alignment.** `tripstate.__version__` tied to the spec version; `tools/release.py` tagging store `schema_version`. | D-13 discipline at the package level. | — | S |

## E. Desk research still open

| # | Item | Why | Effort |
|---|---|---|---|
| E1 | **Vincennes track geometry** (GP/PP lengths, widths, bend radii, the "montée") from public descriptions → realistic simulator (A1) and the RP-19 rail/fence scale aid. | Makes the synthetic numbers track-specific. | S |
| E2 | **SAM 2 / SAM 2.1 throughput model**: memory-bank cost per object, batching options, DAM4SAM/SAM2MOT speed figures → expected frames/s at 14 objects. | Pre-answers R-15 before C4 runs. | S |
| E3 | **French racing-comment NLP**: spaCy French pipelines, rule-based vs LLM extraction, published work on sports commentary parsing → design for A3's evaluation. | Right tool for the text workstream. | S |
| E4 | **External validation of trip signal**: whether any public harness dataset carries parked/cover flags that could test the signal hypothesis before the owner's corpus. | A second, independent look at R-1. | S |

## Suggested order

1. **A1** (simulator with perspective and bends) — biggest reduction of geometric uncertainty for zero owner time.
2. **A2 + A3** (signal gate harness and text parser) — the go/no-go becomes runnable; also useful on its own.
3. **B1, B2, B3** (M1, M3 checks, runner QC) — no stubs left; the synthetic end-to-end run covers every module.
4. **A5, A4, B6** (promotion script, calibration harness, DoD runner) — the freeze-to-release path becomes mechanical.
5. **C3, C4, C6, C7** (fingerprint, compute plan, rehearsal, operator card) — the owner's first real day is de-risked.
6. **D1, D2** (decision memos, invariant tests) — governance and robustness.
