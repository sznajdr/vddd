# Audit log — coherence checks and fixes

Each entry: what was checked, what was wrong, what changed. Dates are when the fix landed.

| Date | Area | Finding | Fix |
|---|---|---|---|
| 2026-11-04 | M5 classify × §2.2 | At an **exact** longitudinal tie, swapping the two runners' coordinates was a no-op, so the saddle-number tiebreak silently decided LEADER vs RAIL_UNCOVERED, which §2.2 forbids. | Ambiguity check now reverses the *ordering* of adjacent near-tied runners and compares resulting states; regression test `test_exact_tie_is_unknown_not_tiebreak`. |
| 2026-11-04 | M0 video × acceptance | `-fps_mode cfr -r 25` produced 52 frames from a 2 s / 30 fps clip (2-frame overrun), failing the ≤ 1-frame duration rule. | Rate conversion via the `fps` filter (drop/dup, no interpolation); duration check kept strict. |
| 2026-11-04 | M7 gates | With anchors missing, undefined coverage also appended `coverage_*_low`, implying a measured low coverage. | Coverage codes only when anchors exist; undefined coverage with anchors present raises (pipeline bug, not a gate outcome). |
| 2026-11-04 | M7 coverage | Overlapping pack-coherent intervals would have been double-counted. | Intervals merged before summing. |
| 2026-11-04 | Schema `events` | `saddle_no` nullable inside the primary key; race-level `SHOT_GAP` ambiguous. | `saddle_no = 0` means race-level; table-level CHECK ties it to `type = 'SHOT_GAP'` (placed after the column list — the first attempt put it mid-list, which SQLite rejects). |
| 2026-11-04 | Ledger L-12 | Ledger wording widened `lead_uncovered_outside` to "uncovered tier ≥ 2", beyond 1.2.0's PARKED-only definition. | Reverted to the uniquely furthest-advanced `PARKED` runner; RP-11 recorded for the D-26 table gap. |
| 2026-11-04 | Registry × thresholds | `detach_sl` flagged evidence-gated although only its prevalence is checked; `axis_neighbourhood_k` flagged without a registry entry. | `detach_sl` unflagged (prevalence is a named check); registry entry added for `axis_neighbourhood_k`. Test `test_registries.py` enforces both directions. |
| 2026-11-04 | Draft cut | Unescaped `\|` in inline math broke a ledger table row (the RP-9 failure mode, reproduced in my own ledger). | Escaped; `lint_spec.py` checks column counts on both spec files in CI. |
| 2026-11-04 | Synthetic tests | Three test fixtures contradicted the closed cover interval `[0.3, 2.0]` or sampled an invisible frame; one manifest pool violated its own break-count constraint. | Fixtures corrected; the code was right each time. |

| 2026-11-04 | Pilot × EC-08 | Identity timelines dropped unsupported frames, so 2 % detector dropouts became single-frame `NOT_VISIBLE` holes and the edit score collapsed to 7 while IoU stayed 0.96. | `coast_gaps`: gaps ≤ `occl_max_s` are linearly interpolated with halved confidence (→ `LOW_CONF`), longer gaps stay `NOT_VISIBLE`; per-runner conf = axis conf × box conf so coasting is visible downstream. |
| 2026-11-04 | Pilot seeded flags | Every runner raised a `lost` flag for the frames before its own prompt. | Flags are prompt-aware (`prompt_frames`). |
| 2026-11-04 | **M4 §3.1 axis (RP-21)** | Per-frame motion axis from ~4 px displacements with 0.3 px jitter tilted up to 7° on some frames; since Δw ≈ (SL/SW)·l·sin δ this merged all lanes and made whole frames `UNKNOWN`. | Length-weighted axial mean, `axis_min_vector_sl` jitter guard, `axis_smooth_s` temporal smoothing that PCA frames never seed; §3.1 text amended (L-10b) with the ≈ 1° accuracy requirement; regression test with jittered boxes. |
| 2026-11-04 | Headless replays | A scripted seeding replay produced wall-clock minutes of ~1e-6 that would have fed KG-1 / Q-7. | `SeedingSession.headless` marker; `pilot_run.py` ignores minutes from headless sessions unless `--human-minutes` is given for dry runs. |

| 2026-11-04 | Simulator (A1) | First study placed the pack at arc length 0 (west end of the home straight, 250 m from a mid-stands camera) and read an end-on view as side-on; a constant-speed pan with constant lag left zero residual image motion. | Pack placed in front of the stands by default; pan wobble added; study positions expressed relative to the stands with a view-angle column. |
| 2026-11-04 | M4 §3.1 axis (RP-22) | Motion axis 5–6° off with zero jitter under a tracking camera (pan + zoom flow). | `axis_source = rail`; rail direction never smoothed (smoothing lagged the rotating direction by ~6°). |
| 2026-11-04 | M4 lateral scale (RP-19) | Linear two-line scale wrong under perspective. | 1-D projective lateral coordinate from rail, fence and vanishing point; polyline datum on bends. |
| 2026-11-04 | M4 centroid (RP-23) | `(mid-x, max-y)` carries ≈ 1 SW pan-dependent lateral bias; absolute tiers failed at the closed `rail_attach_sw` boundary. | Foot-point correction in projective mode. |
| 2026-11-04 | Study metric | Undetected (out-of-frame) runners counted as tier failures. | Detected runners only; visibility is EC-02's business. |

| 2026-11-04 | Registry × draft markers (A5) | The draft marks `normalized_fps` and `stratum_yield_review_factor` `[EG]` but the registry had no entries for them, and TS-0.0.0 flags `sw_ratio` `eg: true` without a registry entry — `freeze_check` could have passed with markers left in the spec (D-36 rule (1) unverifiable). | Registry entries added for `normalized_fps` (instrument: `sheet_race.csv` fps) and `sw_ratio` (confirmed iff `sw_ratio_location_variation` ≤ 2.0, RP-5); `instantiate_eg.py` fills both. `stratum_yield_review_factor` has no instrument → left unbound as an owner decision (below). `freeze_check` now binds every `[EG]` marker and lists unbound ones; `test_registries.py` whitelist shrunk to that one key. |
| 2026-11-04 | lint_spec × frozen threshold set (A5) | `check_eg_keys` used `load_default()`, which after a promotion resolves to the frozen set (all `eg: false`), producing 17 false "not flagged eg" problems. Found by the real-run rehearsal on a repository copy. | Lint loads `TS-0.0.0-provisional.yaml` explicitly: the rule "registry keys are flagged eg in the provisional set" holds forever. Lint additionally rejects any `[EG`/`[OPEN` marker in a FROZEN file. |
| 2026-11-04 | Numbers are config (A4/B6) | DoD floors (0.85, 0.80, 10 breaks, 5 min, 20 attempts, 8/10) and §7.2 constraints (mask floors, load cap, 10 pt gap) would have been hard-coded in the new tools. | New TS namespaces `release` and `calibration` (D-18); `dod3_median_target_min` is a TS key flagged `eg: true` (its registry entry already existed). |
| 2026-11-04 | Synthetic calibration fixture | First layouts put two offsets exactly on a floating-point boundary (0.9 / 0.8 SW) and the held-out race was insensitive to wrong thresholds, so the > 10 pt gap rule could not fire. Found by the tests. | Margins ≥ 0.05 SW everywhere; the held-out race carries both discriminating mechanisms; the optimum is strict (every neighbour one grid step away scores lower). |
| 2026-11-04 | Synthetic release store | The recall-miss condition could never produce more than two misses, so a failing DoD-2 was untestable. | Misses spend a budget across held-out races; `recall_misses=4` now fails DoD-2 and makes the second store's canonical events differ (DoD-5 fail path tested). |
| 2026-11-04 | Handoff text | "Changelog row template already in the draft's changelog" — the template is in the ledger (`SPEC-2.0.0-draft-LEDGER.md` row `2.0.0 | _at freeze_`), not in the draft. | `promote.changelog_row` follows the ledger template; no draft edit needed. |
| 2026-11-04 | pilot/report.py × D-18 | `evaluate_kill_gates` hard-codes the gate thresholds (8, 0.85, 0.40, 2.0) that `kill_gates.yaml` carries. | Not changed in this block (tests pin the function signature); listed below as hygiene. |

## Disposition after delegated decisions (2026-11-04)

Earlier table rows are historical findings. The owner delegated the remaining verdicts; `docs/decisions/2026-11-04-continuation.md` supersedes their pending wording.

- RP-11 fixed: LEADER precedence with independent cover, tested.
- Policy EG markers/TS flag removed; real and synthetic registries now match. All draft markers bind.
- Three OPEN markers resolved through reproducible ledger edits; optional rail/projective geometry accepted with EC-13 abstention.
- SHOT_GAP saddle 0 and human chart version-column design retained.
- Operator heading now references config keys rather than repeating provisional numbers.
- Pilot cutoffs now read the selected registry, including write-back; regression changes all four cutoffs.
- Release review fixed missing/split-mismatched held-out charts and cross-producer BREAK contamination; three regression cases added.
- Windows isolated-promotion test now keeps UTF-8 mode in its minimal child environment.
- Ruff conventions explicitly retain established compact reference code and mathematical names, with import bootstrapping permitted only in tools; the lambda and redundant semicolon were fixed.

Remaining work is the implementation queue in the handoff plus real external evidence. No unresolved design approval is a blocker.
