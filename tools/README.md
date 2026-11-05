# tools/ — command-line entry points

Every tool is a thin CLI over `src/tripstate/` (logic lives in the package, tests cover the package). "Runs today" says what a clean checkout can do without replays; nothing marked **real inputs** has ever run on footage. `make help` lists the targets that chain them.

## Spec lifecycle (D-36)

| Tool | Does | Runs today |
|---|---|---|
| `cut_draft.py` | regenerates `spec/SPEC-2.0.0-draft.md` from 1.2.0 + the ledger; `--check` in CI | yes (`make cut-draft`, `make check-draft`) |
| `lint_spec.py` | table hygiene, decision references, EG flags, no markers in a FROZEN file | yes (`make lint-spec`) |
| `lint_docs.py` | documentation hygiene: referenced paths exist, every tool/package is indexed, `make` targets exist | yes (`make lint-docs`) |
| `freeze_check.py` | the D-36 gate: registry instantiated, KG-1…KG-4 pass, every `[EG]` marker bound, no `[OPEN]` | yes; exits 1 until OD-1x and the pilot (`make freeze-check`) |
| `instantiate_eg.py` | OD-1x sheets + pilot reports → proposed registry values (dry run prints only) | synthetic fixture (`make freeze-dry-run`, `make od1x-rehearsal`); **real inputs**: `data/od1x/` |
| `promote_draft.py` | the promotion itself: FROZEN spec, frozen threshold set, decision log, `version.py`; idempotent | `--dry-run` only (`make freeze-dry-run`); the real run refuses while `freeze_check` fails |

## Owner protocols (P2–P4)

| Tool | Does | Runs today |
|---|---|---|
| `od1x_rehearsal.py` | the owner's OD-1x afternoon with synthetic inputs, checked against the committed fixture | yes (`make od1x-rehearsal`) |
| `od1x_timer.py` | stopwatch for OD-1x step 1 → `sheet_seeding.csv`; `--script` = REHEARSAL rows only | yes |
| `synth_video.py` | renders the scripted synthetic race to a real clip + truth + seeds + headless seeding script | yes (needs ffmpeg) |
| `seed_cli.py` | the seeding tool (OpenCV window or `--script` headless replay; live engines oracle / detector / SAM 2) | headless yes; window needs a display; SAM 2 / detectors **real adapters unverified** |
| `pilot_run.py` | one pilot race on the seeded or detector path → `report_<path>.json` | synthetic yes (`make pilot-demo`); **real inputs**: replays + adapters |
| `pilot_report.py` | aggregates pilot reports → `pilot_report.md`, writes KG-1…KG-4 into `kill_gates.yaml` | yes on synthetic reports |
| `signal_gate.py` | the pre-registered signal gate (KG-5) on a runner-race corpus | synthetic dry run yes; **real inputs**: the owner's corpus |
| `parse_notules.py`, `lexicon_attest.py` | §11 text parsing into `hand_charts`-shaped rows; `[C]` attestation on a corpus | synthetic yes; **real inputs**: notule corpus |
| `geometry_study.py` | the simulated OD-1x step 4 (research 11) | yes |

## After the freeze (P5–P6)

| Tool | Does | Runs today |
|---|---|---|
| `golden_manifest.py` | §6.1 dev/held-out manifest: `build` (refused while DRAFT), `validate`, `check-split`, `diff` | validate/check/diff yes; build refused |
| `boris_to_hand_charts.py` | BORIS export → `hand_charts` + `events` JSON (RP-17) | yes on a BORIS TSV |
| `export_calibration_inputs.py` | pipeline frame JSON + store + manifest → `data/calibration/` sidecars and charts (C8) | synthetic yes; **real inputs**: a pipeline run |
| `calibrate.py` | §7.2 grid search → `TS-x.y.yaml` with provenance; `--heldout` once | `--synthetic` only (`make calibrate-dry-run`); real run refused while DRAFT |
| `evaluate_release.py` | DoD-1…6 → `data/releases/<version>/evaluation.md` + changelog row | `--synthetic` (`make evaluate-dry-run`); **real inputs**: a store + manifest |
| `env_fingerprint.py` | `versions.determinism_env` (D-32): actual versions and flags, null when absent | yes |

Conventions: every tool has a module docstring with its usage line; numeric cutoffs come from `config/thresholds/` (D-18); tools bootstrap `src/` on `sys.path` (ruff E402 allowed only here); no tool invents evidence — dry runs write to temp dirs and mark their rows synthetic.
