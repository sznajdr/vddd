# STATUS — live board

_Last updated: 2026-11-04 (freeze-to-release tooling: A5 promotion, A4 calibration harness, B6 DoD evaluation)._ Update this file whenever a phase gate moves.

## Phase

**P1 complete: `spec/SPEC-2.0.0-draft.md` is the full prose draft** (cut from 1.2.0 by `tools/cut_draft.py`, 63 edits; the ledger stays as `SPEC-2.0.0-draft-LEDGER.md`). **Next: P2 (OD-1x) and P3 (signal gate)**, both owner-side. P4's throwaway pilot stack exists and runs end to end on synthetic video; on real replays it needs the model adapters (Grounding DINO / OWLv2 / YOLO, SAM 2) run once and the seeding window exercised with a display. **The freeze → calibration → release path is now tooled and rehearsed on synthetic fixtures** (`tools/promote_draft.py`, `tools/calibrate.py`, `tools/evaluate_release.py`; `make freeze-dry-run calibrate-dry-run evaluate-dry-run`). None of it has run for real: `freeze_check` still blocks on 19 EG entries, 4 kill-gates, 2 unbound markers and 3 open owner decisions.

## Facts established

- Spec lineage: 1.0.0 → 1.1.0 → 1.2.0, all dated 2026-07-25, all FROZEN. 1.x line closed.
- Review (2026-07-25) and RECON (2026-07-26) exist and are reconciled; residual conflicts: none claimed by RECON, several gaps found afterwards (see `spec/RECON-2.0.0-patches.md`).
- No footage has been inspected. OD-1 / OD-1x: **not run** (as far as this repo knows).
- No replays are in hand; replay source and rights unverified.
- Notule corpus and NLP artifacts referenced by §11 live outside this repo (owner's machine).

## Open questions for the owner

1. Has OD-1x, or any replay pull, happened since July 2026?
2. Where do the replays and the notule corpus live? Paths or a mount are needed for `data/`.
3. The signal gate is runnable: point `tools/signal_gate.py --corpus` at a runner-race CSV with closing odds and notules (see `protocols/SIGNAL-GATE`). Needs your corpus.
4. Do LeTrot's "Tracking" pages (per-runner tracking data at Vincennes) expose anything usable? If per-runner positional data exists officially, large parts of the CV plan are replaceable. Decide before P4.
4. Replay rights: Equidia terms were not read to completion. Confirm personal-use replay access is acceptable for the intended use.
5. **`stratum_yield_review_factor` (0.5, §6.2/§7.1) is marked `[EG]` in the draft but has no instrument and no registry entry.** It is a D-35 review-trigger policy number. Decide: (a) remove the marker by a ledger edit so it is ordinary D-18 config tuned in §7 (recommended), or (b) add a registry entry with a real instrument. `freeze_check` and `promote_draft` refuse while it is unbound.
6. The three `[OPEN]` markers in the draft (RP-11 table gap, RP-19/RP-22/RP-23 geometry carve-out, the §7.1 `rail_fence` row) must be resolved by ledger edits (`tools/cut_draft.py`) before the promotion: `promote_draft.py` refuses while any remains; the dry run simulates their resolution with `--strip-open-markers`.

## Blockers

| Blocker | Blocks | Owner |
|---|---|---|
| OD-1x not run | P5 freeze, every EG value | owner |
| Replays not sourced | P2, P4 | owner |
| Signal gate not run | go/no-go on the whole project | owner |
| `stratum_yield_review_factor` unbound; 3 `[OPEN]` markers | P5 promotion (`promote_draft.py` refuses) | owner |

## Done

- [x] P0 repo scaffold, EG + kill-gate registries, threshold set TS-0.0.0-provisional
- [x] M0 metadata normalization implemented + tested (incl. S-3 statuses, `plausible_km_rate_min_s = 65`)
- [x] M4 tier clustering with `max_tier_span_sw` largest-gap split + D-26 cover predicate, tested (14-runner spread fixture)
- [x] M5 base-state table incl. `lead_uncovered_outside`, tested
- [x] M7 gate logic Q-1…Q-7 with closed failure codes, tested
- [x] M8 canonical export with fixed-decimal quantization (D-32), tested
- [x] `freeze_check.py` (fails while EG markers remain — expected)
- [x] `instantiate_eg.py` verified on synthetic sheets (dry run)
- [x] M0 video normalization (ffmpeg CFR, hashes, idempotent) + synthetic-clip tests
- [x] M5 smoothing + segment emission + DETACHED overlay, synthetic-trajectory tests (M5 DoD)
- [x] M7 SHOT_GAP events + coverage fractions
- [x] §6.2 metrics (mask IoUs, headline, Wilson CI, break matching, edit score, F1@k) + §6.4 audit sampler with operating characteristic
- [x] Research pack `docs/research/` (10 notes + sources) and `docs/STACK-2.0.md`
- [x] P1: full prose SPEC-2.0.0-draft cut reproducibly (`tools/cut_draft.py --check` in CI)
- [x] M4 principal-axis projection (`ShotProjector`) + synthetic race simulator; end-to-end M4→M5→M7→M8 test passes against scripted truth
- [x] M8 SQLite store (DDL, chartable-only reads, structural D-11 guard, canonical SHA per table, version coexistence)
- [x] M6 uncalibrated reference detector; golden manifest tool (§6.1, S-6); BORIS→hand_charts converter (RP-17)
- [x] CI workflow, `tripstate` CLI (`ingest-video`, `synth-demo`, `evaluate`), audit fixes (`docs/AUDIT.md`)
- [x] Seeding tool: `SeedingSession` state machine (keymap, auto-slowdown at flags, anchors, orientation, break review, first-past, recall, human-minutes) + `tools/seed_cli.py` (OpenCV window / headless script)
- [x] M1 shot segmenter scaffold (adaptive cut detector + histogram signal, blob/CLIP type classifier, overlay mask with EC-06 merge, replay cadence, evaluators) on a synthetic broadcast; M3 finish/start checks with the D-30 fixtures; M7 runner QC
- [x] Text-parse skeleton (`tripstate.textparse`): §11.2 lexicon as dimension assertions, candidate sets, §11.4 phases, negation/quote/other-subject scope, BREAK events, exclusions, reserved families; `tools/parse_notules.py`, `tools/lexicon_attest.py`
- [x] Signal gate (`tripstate.signal`): prior-race indicators with leakage guard, numpy logistic regression vs market baseline, holdout + bootstrap CI + fold stability, pre-registered `decision.yaml`; `tools/signal_gate.py` (synthetic dry run and real corpus, KG-5 update)
- [x] World-space simulator (`tripstate.synth.track/camera/world`): stadium track in metres, pinhole grandstand camera, 3-D vehicle boxes; `tools/geometry_study.py` → `docs/research/11-simulated-geometry.md`; projector gains `axis_source = rail`, `lateral_scale_mode = rail_fence_projective` with polyline datum and foot-point correction (RP-19…RP-25)
- [x] Live seeding loop (`tripstate.seeding.live`): oracle / detector / SAM 2 engines, `FlagMonitor`, pause-on-flag, re-seed prompts, session timeline → `pilot_run.py --propagator session`
- [x] **A5** `tools/promote_draft.py` + `tripstate.release` (freeze check with `[EG]` marker binding, OD-1x/pilot instantiation, promotion: FROZEN header + freeze record, D-26…D-36 into §1, markers → frozen values, changelog row, `TS-2.0.0-frozen.yaml`, decision log Pending → Closed, `version.py` bump; dry run with diffs; real run rehearsed on an isolated repo copy, idempotent). Registry entries added for `normalized_fps` and `sw_ratio`; `instantiate_eg.py` fills them and the D-29 pilot keys (`--pilot-reports`)
- [x] **A4** `tripstate.calibration` + `tools/calibrate.py` (geometry sidecars with pack-space re-derivation, grid search on dev charts with the §6.2 headline and config constraints, provenance-carrying TS writer, one-shot held-out with the > 10 pt rule; `--synthetic` recovers mis-set `cover_lat_sw` / `same_tier_sw` exactly; real run refused while DRAFT). DoD floors and §7.2 constraints now live in TS namespaces `release` / `calibration` (D-18)
- [x] **B6** `tools/evaluate_release.py` + `tripstate.release.evaluate` (DoD-1…6 with pass/fail/invalid reasons, Wilson CI, dual headline with/without Q-7, per-stratum yield and headline, `data/releases/<version>/evaluation.md` + changelog row; `--synthetic` store, two runs for DoD-5)
- [x] Throwaway pilot stack (`tripstate.pilot`): ffmpeg frame source, synthetic video renderer, oracle + blob detectors, IoU tracker, seed→track assignment with flags, oracle + SAM 2 propagators, IDF1/IDSW/MOTA-lite, race runner → report, kill-gate aggregation; `tools/synth_video.py`, `pilot_run.py`, `pilot_report.py`; `make pilot-demo` runs the loop on synthetic video

## Research pack (2026-11-04)

`docs/research/00-INDEX.md` — 13 findings mapped to modules and decisions; proposals RP-12…RP-20 in the patch list; proposed §13 stack in `docs/STACK-2.0.md`. Access/rights questions (replays, official tracking) are out of scope by owner decision.

## Owner decisions pending (see `spec/RECON-2.0.0-patches.md`)

- RP-5 lateral scale: per-shot `sw_ratio` if OD-1x shows > 2× variation.
- RP-6 LeTrot tracking data: read the pages before P4.
- RP-11 D-26 table gap: tier-1 leader covered by an outside runner. Recommended: keep `LEADER`, record `covered = true`.
- RP-12 seeded SAM 2 propagation as the M3 default (biggest design consequence of the research).
- RP-14 / RP-15 / RP-17 stack and metric additions (low risk, recommended).
- RP-19 / RP-20 geometry aids (only if OD-1x step 4 shows the lateral problem).
- RP-21 axis-accuracy requirement (≈ 1° on a 5 SL pack): already applied as §3.1 text L-10b and code; confirm.
- **RP-19 (refined) / RP-22 / RP-23 / RP-24 / RP-25** from the simulator: adopt the rail-line axis and the projective lateral coordinate (needs a §3.3 carve-out), decide how to handle sections without lateral resolvability. These are the largest open design questions in M4 now.
- **Freeze mechanics (A5 findings):** `stratum_yield_review_factor` marker without instrument (question 5 above); the three `[OPEN]` markers block `promote_draft.py`; the §5.1 heading's "target median ≤ 5 min" carries no `[EG]` marker although DoD-3's 5 is evidence-gated (ledger edit suggested so the heading cannot go stale at the freeze).
