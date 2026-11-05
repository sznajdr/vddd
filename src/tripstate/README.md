# tripstate — package map (SPEC-2.0.0-draft §4 M0…M8 and the lifecycle around them)

Every numeric cutoff is read through `config.ThresholdSet` (D-18). "Reference" means a pure-function implementation of a structurally frozen rule, tested on synthetic data; nothing has seen a frame of real video.

| Package | Spec | Status |
|---|---|---|
| `m0_ingest/` | §4 M0 | metadata normalization + ffmpeg video normalization, tested |
| `m1_shots/` | §4 M1 | scaffold on a synthetic broadcast (adaptive cut detector, type classifier interface, overlay mask) |
| `m2_detect/` | §4 M2 | stub (needs the golden manifest for a race-disjoint holdout) |
| `m3_track/` | §4 M3 | finish/start/anchor checks; `id_assignments` writer with RP-18 click provenance |
| `seeding/` | §4 M3 tool DoD | operator-loop state machine (`SeedingSession`) + live engines and flag monitor |
| `m4_geometry/` | §2.2, §3 | tiering, cover, principal-axis projection (`ShotProjector`), frame JSON record |
| `m5_states/` | §2.3–2.4, §3.4 | classification, smoothing, segment emission |
| `m6_events/` | §4 M6 | `positions_lost`; uncalibrated break-candidate reference |
| `m7_qc/` | §10, §6.2 | gates Q-1…Q-7, per-stratum yield, SHOT_GAP, coverage, runner QC |
| `m8_storage/` | §9 | canonical export (D-32), SQLite store with additive migration, environment fingerprint |
| `schema/` | §9 | DDL and closed enums |
| `evaluation/` | §6.2–6.4 | metrics, per-race/per-set scoring, identity audit sampler |
| `golden/` | §6.1 | manifest builder and checks (build refused while DRAFT) |
| `charting/` | §5.2 | BORIS export converter |
| `textparse/` | §11 | lexicon bridge, candidate sets, phases |
| `signal/` | KG-5 | signal-gate harness |
| `synth/` | — | scripted pack-space races, world-space simulator; never evidence |
| `pilot/` | protocols/PILOT-5 | throwaway pilot stack (`producer_kind = pilot_throwaway`) |
| `calibration/` | §7.2 | sidecars, grid search, provenance, held-out rule; refused for real while DRAFT |
| `release/` | D-36, §0.2 | freeze check, marker binding, instantiation, promotion, DoD evaluation, synthetic store |

`config.py` loads threshold sets; `version.py` holds `SPEC_VERSION` / `SPEC_STATUS` (bumped only by `tools/promote_draft.py`); `cli.py` is the `tripstate` command (`ingest-video`, `synth-demo`, `evaluate`).
