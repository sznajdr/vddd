# Architecture

## Module graph (§4.0) and what exists today

```
replay + metadata
      │
      ▼
 M0 ingest ──────────── metadata rules + ffmpeg video normalization IMPLEMENTED
      │
      ▼
 M1 shots ───────────── scaffold IMPLEMENTED (synthetic broadcast) ─┐
      │                                                             │ G-1
      ▼                                                             │
 M2 detect ──────────── stub (needs golden manifest for holdout)   ─┘
      │
      ▼
 M3 track + seeding ─── checks + live seeding loop + id_assignments writer (RP-18) IMPLEMENTED ─┐ G-2
      │                                                                     │
      ▼                                                                     │
 M4 geometry ────────── tiering + cover + axis projection IMPLEMENTED       ─┘
      │                                                                     ┐ G-3
      ▼                                                                     │
 M5 states ──────────── classification + smoothing + segments IMPLEMENTED  ─┘
      │
      ▼
 M6 events ──────────── positions_lost + UNCALIBRATED reference detector IMPLEMENTED
      │
      ▼
 M7 QC ──────────────── gates + yield + SHOT_GAP + coverage + runner QC IMPLEMENTED
      │
      ▼
 M8 storage ─────────── canonical export + SQLite store IMPLEMENTED
 evaluation ─────────── §6.2 metrics + §6.4 audit sampler IMPLEMENTED (tripstate.evaluation)
 synth ──────────────── scripted races → pixel boxes; end-to-end test M4→M5→M7→M8 passes
 golden / charting ──── manifest tool (§6.1) and BORIS converter (RP-17) IMPLEMENTED
 pilot / seeding ────── throwaway stack: ffmpeg frames, oracle/blob detectors, IoU tracker, seed assignment,
                        oracle/SAM2 propagation, IDF1/IDSW, race runner, kill-gate report; seeding-session core + CLI
 release ────────────── D-36 freeze check (registry + kill-gates + [EG] marker binding), OD-1x/pilot instantiation,
                        promotion DRAFT → FROZEN, DoD-1…6 release evaluation — IMPLEMENTED, rehearsed on synthetic fixtures
 calibration ────────── §7.2 harness: geometry sidecars → re-derived tiers → M5 → headline; grid search, provenance,
                        held-out gap rule — IMPLEMENTED, refused for real while DRAFT
```

Run the chain yourself: `tripstate synth-demo` (per-runner mask IoUs and edit scores against the scripted truth, gates, canonical SHA).

"IMPLEMENTED" means a pure-function reference implementation of a structurally frozen rule, reading every number from a threshold set. None of it is calibrated. None of it has seen a frame of video.

## Two stacks, one schema

| | Production stack (M0→M8) | Throwaway pilot stack (`protocols/PILOT-5`) |
|---|---|---|
| Purpose | the corpus | freeze evidence (KG-2, KG-3, budget distribution) |
| Gates | G-1…G-4 apply | exempt (RP-2) |
| Outputs | `producer_kind ∈ {cv_extract, human_chart, text_parse}` | `producer_kind = pilot_throwaway`, quarantined after freeze |
| Shares | schema (§9), threshold set, `tripstate.m4_geometry`, `tripstate.m7_qc` | |

## Data flow for one race (production)

1. `M0` writes `races`, `runners`, normalized video, hashes.
2. `M1` writes `shots`; wide-pan intervals gate everything downstream.
3. `M2` writes detections per wide-pan frame (sidecar).
4. Operator loop (`M3`, ≤ budget): orientation confirm → `t_0`/`t_end` → seed → tool auto-plays at ≥ 2× → re-seeds on flags → break review. Writes `id_assignments`, `race_anchors`, `shot_calibrations`, human-minutes.
5. `M4` projects to pack-space per frame; `M5` classifies + smooths into `state_segments`; `M6` proposes `BREAK` candidates → review → `BREAKING` overlays.
6. `M7` computes coverage, runs Q-1…Q-7, writes `qc`, `runner_qc`, `SHOT_GAP`.
7. `M8` persists; canonical JSONL + SHA-256 for DoD-5; default views join `chartable = true`.

## Determinism boundary (D-32)

Full-precision floats everywhere inside the pipeline. Quantization happens once, in `m8_storage.canonical`, for the hashable export. GPU nondeterminism is tolerated at the detection layer and absorbed by quantization; environment knobs are recorded under `producer_version`.

## Freeze → calibration → release (tooling, rehearsed; nothing has run for real)

```
OD-1x sheets + pilot reports ──instantiate_eg.py──▶ evidence_gated.yaml (instantiated)
pilot reports ────────────────pilot_report.py────▶ kill_gates.yaml (KG-1…KG-4 statuses)
                                                        │
                      freeze_check.py  = tripstate.release.freeze: EG instantiated? gates pass? every `[EG]` marker
                                          in the draft bound to a registry entry / kill-gate? no `[OPEN]` left?
                                                        │ exit 0
                      promote_draft.py = tripstate.release.promote (one commit):
                          SPEC-2.0.0-draft.md ──▶ SPEC-2.0.0.md   (FROZEN header + freeze record; D-26…D-36 in §1;
                                                                   markers → frozen values; changelog row; §7.1 → frozen TS)
                          TS-0.0.0-provisional ──▶ TS-2.0.0-frozen.yaml (registry values, eg: false, search_provenance: freeze)
                          DECISION-LOG.md       ──▶ Pending → Closed (SPEC-2.0.0 §1)
                          version.py            ──▶ SPEC_VERSION 2.0.0, FROZEN  (load_default() then returns the frozen set)
                                                        │
   golden_manifest.py build (now allowed) → hand charts (OD-3) → pipeline runs → data/frames/<race>.frames.json (M4 record)
                      export_calibration_inputs.py: frames + store hand_charts + manifest → data/calibration/ (sidecars + charts;
                          refuses S-6 mismatches and ambiguous human producers)
                                                        │
                      calibrate.py = tripstate.calibration: grid over config/calibration/search-space.yaml on DEV races,
                          candidate TS → re-derive tiers from stored geometry → chart_race → §6.2 headline; constraints from
                          TS `calibration` namespace → TS-2.x.yaml (calibrated: true, search_provenance) → --heldout ONCE
                          (> heldout_gap_max_pt → spec_revision, not more tuning)
                                                        │
                      evaluate_release.py = tripstate.release.evaluate: store(+ second run) + manifest → DoD-1…6 with
                          pass/fail/invalid reasons, headline with/without Q-7 (D-35), per-stratum tables,
                          data/releases/<version>/evaluation.md + §14 changelog row draft
```

Every floor and constraint these tools apply is a threshold-set value (`release` and `calibration` namespaces, D-18).
Rehearsals that never touch the repository: `make freeze-dry-run` (synthetic OD-1x sheets → instantiated registry →
simulated promotion with diffs), `make calibrate-dry-run` (mis-set thresholds recovered), `make evaluate-dry-run`
(synthetic store, every DoD line). The real promotion additionally rehearses itself in `tests/test_promote_draft.py`
on an isolated copy of the repository (idempotent second run, `freeze_check` green afterwards).


## Continuation decisions (SPEC-2.0.0-draft, 2026-11-04)

Ledger L-46…L-50 resolves the design queue; see `docs/decisions/2026-11-04-continuation.md`. M5 leadership and cover are independent. Rail/projective geometry is an accepted opt-in mode, with EC-13 abstention when unresolved; existing defaults remain reproducible. Intended model stacks are approved, while real adapters remain implementation tasks. Pilot gate evaluation reads the selected registry, and release evaluation rejects missing or split-mismatched truth and scopes CV events to the selected producer. D1 is complete; continue the handoff coding queue without waiting for another design approval.
