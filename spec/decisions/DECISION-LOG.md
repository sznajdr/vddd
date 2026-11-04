# Decision log

Append-only. Closed decisions MUST NOT be re-litigated by agents. Reopening = MAJOR bump + owner sign-off.

## Closed (SPEC-1.2.0 §1) — D-01…D-25

Full text in `spec/SPEC-1.2.0.md` §1. One-line index:

| ID | Decision |
|---|---|
| D-01 | Identity = human-in-the-loop seeding; OCR/silk re-ID banned in v1 |
| D-02 | One shot type (main wide pan); no stitching |
| D-03 | v1 states: cover, width tier, rank, breaks; stretch-block → v1.5 |
| D-04 | (see spec) |
| D-05 | Schema is the stable artifact; CV, human, text all fill it |
| D-06 | Vincennes, attelé, ≤ 14 runners |
| D-07 | Pack-relative coordinates in SL/SW; pixels banned |
| D-08 | State definitions frozen; numeric thresholds are config |
| D-09 | Shot segmenter gates tracker; human budget; skip-don't-rescue |
| D-10 | `t_0` / `t_end` = one click each |
| D-11 | Coverage is first-class; `unchartable` excluded, no partial credit |
| D-12 | OD-1 inspection before "production-real" |
| D-13 | Versioning on every artifact |
| D-14 | Agents-first spec register |
| D-15 | Normative = contracts + tests; stack non-normative |
| D-16 | Build order M0→M8; minimal keyboard seeding tool |
| D-17 | Golden fixtures + quantified acceptance; PARKED/cover weighted highest **(reopened by D-27 → MAJOR)** |
| D-18 | Versioned threshold set + calibration procedure |
| D-19 | Living edge-case registry |
| D-20 | Lexicon bridge |
| D-21 | Single markdown, semver, changelog, out-of-scope register |
| D-22 | Per-runner start distance is metadata, never a geometry correction |
| D-23 | `t_end` = first past the post |
| D-24 | Official time normalized with unit provenance |
| D-25 | First-past resolution ladder; `arrival_revised` never defaulted |

## Pending — appended to §1 at the 2.0.0 freeze (RECON §3)

Agreed direction; may be built against; not yet FROZEN.

| ID | Decision | Rationale |
|---|---|---|
| D-26 | Cover is a tier-independent geometric predicate (`cover_lat_sw`, `cover_min_sl`, `cover_max_sl`); tiers label states, geometry decides cover. Tier clusters are span-bounded (`max_tier_span_sw`) with deterministic largest-gap splitting. | The money metric must not inherit clustering artifacts. |
| D-27 | Headline money component = uncovered-outside mask IoU (`tier ≥ 2 ∧ ¬covered`), weights 0.5/0.3/0.2; `first_over` → `lead_uncovered_outside` (positional sense). | Measure the physics, not the label boundary. |
| D-28 | `DETACHED` is diagnostic-only: excluded from headline `rest`; empty-union invalidation scoped to DoD-1 components. | A deliberately rare overlay must not be able to invalidate an evaluation. |
| D-29 | Budget cap ≠ budget target: Q-7 cap 8 min (≈ p90 of pilot at re-instantiation), DoD-3 median ≤ 5 min; seeding tool provides ≥ 2× playback with event slowdown. | A hard cap truncates a tail; it must not bisect the distribution. |
| D-30 | `official_assumed` requires ≥ `finish_evidence_min_k` observed crossings consistent with the reference; zero-evidence adoption is forbidden. | A corroborator with no observations is not a corroborator. |
| D-31 | Statistical honesty package: DoD-2 as point estimate + reported CI; §6.4 stratified sampling with stated operating characteristic; `positions_lost` requires an identical visible set. | The spec refuses to overclaim elsewhere; metrics must too. |
| D-32 | Cross-machine determinism via fixed-decimal canonical quantization; environment knobs pinned and recorded; bit-exact hex demoted to optional same-env CI. | The strictest representation must not be paired with the least reproducible producer. |
| D-33 | Kill-gates (§0.4): the project defines when to stop, not only when it is done. Pilot runs on a throwaway stack exempt from G-1…G-3 (RP-2). | Cheap insurance against sunk cost; extends D-09's posture to the project level. |
| D-34 | Anchor QC uses per-start-type bias offsets + tolerances, measured before frozen; unverified tolerances are treated like unverified units. | The D-24 failure mode, one tolerance over. |
| D-35 | Yield is instrumented per stratum with a differential-yield review trigger; headline accuracy reported with and without Q-7 failures. | Gate outcomes are MNAR for the same reason coverage is. |
| D-36 | DRAFT-until-evidence: EG markers block promotion; one freeze event per major line. | FROZEN is a load-bearing word. |

## Proposed, not yet allocated (owner verdict needed)

| Ref | Proposal | Trigger |
|---|---|---|
| RP-5 | Per-shot lateral scale (`sw_ratio_method`) if OD-1x step 4 shows > 2× variation across track locations. | OD-1x result |
| RP-6 | Use official LeTrot tracking data as a source, if it exists in usable form. Could supersede M2–M4 for rank/position. | Owner reads the pages |
| RP-7 | Signal gate as a project go/no-go, separate from the spec. | Owner runs `protocols/SIGNAL-GATE/` |
