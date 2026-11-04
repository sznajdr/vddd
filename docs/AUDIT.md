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

## Open items found by the audit (owner decisions)

- RP-11 (D-26 table gap), see `spec/RECON-2.0.0-patches.md`.
- `events.saddle_no = 0` convention for race-level rows: confirm or choose NULL with a non-PK surrogate.
- `hand_charts` has no `extractor_version`/`threshold_set_version` columns by design (§9 says they MAY be NULL for human charts); the DDL omits them entirely. Confirm.
