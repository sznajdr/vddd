# STATUS — live board

_Last updated: 2026-11-04 (delegated decisions resolved; code and continuation handoff cleaned)._ Update this file whenever a phase gate moves.

## Phase

**P1 complete: `spec/SPEC-2.0.0-draft.md` is the full prose draft** (cut from 1.2.0 by `tools/cut_draft.py` plus ledger L-46…L-50; the ledger stays as `SPEC-2.0.0-draft-LEDGER.md`). **Next: P2 (OD-1x) and P3 (signal gate)**, both owner-side. P4's throwaway pilot stack exists and runs end to end on synthetic video; on real replays it needs the model adapters (Grounding DINO / OWLv2 / YOLO, SAM 2) run once and the seeding window exercised with a display. **The freeze → calibration → release path is now tooled and rehearsed on synthetic fixtures** (`tools/promote_draft.py`, `tools/calibrate.py`, `tools/evaluate_release.py`; `make freeze-dry-run calibrate-dry-run evaluate-dry-run`). None of it has run for real: `freeze_check` still blocks on 19 EG entries, 4 kill-gates, zero unbound markers and zero open design decisions.

## Facts established

- Spec lineage: 1.0.0 → 1.1.0 → 1.2.0, all dated 2026-07-25, all FROZEN. 1.x line closed.
- Review (2026-07-25) and RECON (2026-07-26) exist and are reconciled; residual conflicts: none claimed by RECON, several gaps found afterwards (see `spec/RECON-2.0.0-patches.md`).
- No footage has been inspected. OD-1 / OD-1x: **not run** (as far as this repo knows).
- No replays are in hand; replay source and rights unverified.
- Notule corpus and NLP artifacts referenced by §11 live outside this repo (owner's machine).

## Continue now

The owner delegated the design queue. Decisions are settled in `docs/decisions/2026-11-04-continuation.md` and applied through ledger L-46…L-50. Claude can proceed with C6, C8, C3, C7, RP-18 schema work and D2; the exact acceptance criteria are in `docs/HANDOFF-NEXT-SESSION.md`. D1 is complete. No further design sign-off is required for that block.

## Remaining external inputs

Replay paths and the notule corpus are not in this checkout. OD-1x, the real signal gate and the pilot still need those inputs and human observations. Official-tracking discovery is optional parallel work, not a reason to stop independent coding.

## Freeze blockers (evidence only)

| Blocker | Blocks |
|---|---|
| 19 uninstantiated OD-1x/pilot registry entries | P5 freeze |
| KG-1…KG-4 not evaluated | P5 freeze |
| Real signal gate / corpus not supplied (KG-5) | Project go/no-go before P4 |

All 20 remaining draft markers bind to the registry or kill-gates. No unresolved policy marker or OPEN decision remains. SPEC_STATUS is still DRAFT; synthetic results do not authorize a real freeze.

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

`docs/research/00-INDEX.md` — 13 findings mapped to modules and decisions; proposals RP-12…RP-20 in the patch list; accepted stack direction in `docs/STACK-2.0.md`. Access/rights questions (replays, official tracking) are out of scope by owner decision.

## Decisions applied

See `docs/decisions/2026-11-04-continuation.md`: LEADER precedence with independent cover, ordinary stratum-review policy, optional rail/projective geometry, accepted SAM 2/TransNetV2/CLIP/BORIS stack direction, approved next seed-provenance schema task, retained event sentinel and human chart versions. Geometry default changes and additional QC/SL rules require measurements; their deferral does not block the coding queue.
