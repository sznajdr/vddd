# Spec Review — Vincennes Attelé Trip-State Extraction Pipeline

**Reviewed:** `spec1_0_0.md` (SPEC-1.0.0) and `spec1_2_0.md` (SPEC-1.2.0)
**Review date:** 2026-07-25
**Scope:** Full read of both documents, §0–§14 + Annex A.
**Status of this document:** Informative. Nothing here is normative; every item is a proposal against a FROZEN spec and would require the §14 bump procedure to adopt.

---

## 0. Verdict

This is a genuinely strong spec — better than most production ML specs. Specifically strong:

- **Abstention semantics are correct in the place everyone gets them wrong.** §6.2 keeps predicted `NOT_VISIBLE` / `UNKNOWN` *inside* the evaluation mask, so they count as misses. Most pipelines silently delete abstentions from the denominator and report inflated accuracy.
- **Operational denominators can't be gamed.** §6.3 forces human-minutes and candidate load to include attempts that later fail QC gates. A failed downstream gate cannot retroactively remove a difficult race from the cost metrics.
- **The determinism contract is real, not aspirational.** §9's canonical JSONL representation (NFC, LF, schema-order keys, versioned-PK sort, deterministic artifact IDs, sidecars by SHA-256) is a testable contract rather than a wish.
- **The decision log makes it agent-executable.** §1 plus RFC-2119 language plus per-module Input/Output/Acceptance/DoD is the right shape for handing to coding agents.
- **Prime directive is enforced structurally, not by exhortation** — EC-13, M4 DoD, M7's diagnostic-only override.

The problem is not rigor. It is **allocation**: three version bumps in one day (1.0.0, 1.1.0, 1.2.0, all dated 2026-07-25) all went into the part of the system that does not require video, while every load-bearing assumption still sits behind an unresolved OD-1.

---

## 1. On the 1.0.0 → 1.2.0 delta

### 1.1 What changed

| Drill | Decisions | Substance |
|---|---|---|
| DR-01 | D-22 | Per-runner `distance_run_m` / `rendement_m`, `start_format` invariants, band-based volte start check, DETACHED interpretation note, start-format golden strata |
| DR-05 | D-23, D-25 | `t_end` pinned to first past the post, crossing-order finish check with revision carve-out, `first_past_saddle_no` / `first_past_method` ladder, `finish_check_basis`, `arrival_revised` never defaulted |
| DR-02 | D-24 | Per-runner time normalization with unit provenance, `official_elapsed_norm_s`, `official_time_method` resolved in M3, EC-12 re-referenced to the first-past runner |

All three are correct fixes. D-23's separation of "the video timeline is geometric, stewards' decisions are not" is exactly right, and D-24's observation that the réduction kilométrique published as the headline "time" would fail EC-12 on every race *while looking like QC working as intended* is the kind of catch that saves a corpus.

The 1.2.0 corpus verification is the best single piece of work in the delta: `time_unit_consistency_tol_s` 2.0 → 0.5, justified against an observed 0.205 s direct-vs-derived ceiling and a ~1.8–1.9 s per-25 m rendement step, which converts a unit-sanity check into a distance-band validator. That is evidence-driven threshold setting done properly.

### 1.2 The prioritization concern

All three drills were **metadata drills**. Metadata is the cheap, already-in-hand, verifiable part. Nothing in 1.1 or 1.2 touches:

- seeding feasibility (the load-bearing assumption of D-01 and the 5-min budget),
- the cover definition (30% of the headline score, a DoD-1 floor),
- tier clustering behaviour under a 14-runner field,
- corpus yield under seven conjunctive gates.

You have verified the manifest of a ship that has not been floated.

### 1.3 A tolerance the same release left unverified

`anchor_duration_tolerance_s` remains **2.0** with no evidence behind it, in the same release that justified a sibling tolerance to three decimals against a 90,451-row corpus.

For a volte, `t_0` is a human click on a moving pack (EC-04: "release into racing direction … as clicked"), compared against an official elapsed time measured from the starter's reference. Systematic bias near or above 2 s is plausible. If it is:

`EC-12 mismatch → anchor_suspect → Q-3 fail → unchartable`

…and a large fraction of volte races silently disappear from the corpus while the logs read as QC working correctly. This is the same failure mode D-24 was written to prevent, one tolerance over.

**Action:** measure operator anchor reproducibility on the OD-1 samples before this number is treated as settled. Consider separate tolerances for `volte` vs `autostart`.

---

## 2. Blocking — resolve before any code is written

### B-1. OD-1 does not test the thing that can kill the project

OD-1 asks about shot composition, % wide-pan, resolution/fps, full-race coverage. It does **not** ask:

> Can the operator assign all 14 saddle numbers from the first stable wide-pan frame, and in how long?

D-01 bans OCR/silk re-ID because reading saddle cloths at broadcast resolution through occlusion is the hardest CV sub-problem in the pipeline (Annex A says so explicitly). That difficulty does not vanish for a human eye looking at the same pixels. Yet the entire human-in-the-loop design (D-01), the ≤ 5 min budget (D-09), and DoD-3 all rest on the assertion that a human can do it quickly — an assertion a 30-minute timed dry run would confirm or falsify.

**Action:** extend OD-1 from "inspect and shot-label" to "inspect, shot-label, and run a timed seeding dry run." See §6.

### B-2. DoD-3 and Q-7 are the same number, so passing the DoD costs half the corpus

- **DoD-3:** median human time per eligible attempt ≤ **5 minutes**.
- **Q-7:** `human_minutes ≤ 5`; `over_budget` is **not waivable** in v1.

If the median lands exactly at target, roughly **50% of races fail Q-7** and become `unchartable`. The operational hard cap and the DoD target must not be the same value.

**Action:** either tighten DoD-3 (median ≤ 3 min, with the 5-min cap catching the tail) or raise the Q-7 cap (~8 min). A hard cap should truncate a distribution's tail, not bisect it.

### B-3. There is no yield floor, and yield will not be missing-at-random

§10 imposes seven conjunctive gates. At an independent 90% pass rate each, yield ≈ 48%. Nothing in the spec estimates, targets, or instruments this. DoD-6 guards it on the 10 held-out races only (8/10 must pass Q-1…Q-6).

Yield will correlate with field size (occlusion, seeding time) and with night footage (detection quality, EC-05) — i.e. exactly the strata whose loss biases the corpus. This is the same argument Annex A makes for why coverage gates are non-negotiable ("missing coverage is *not* missing-at-random"), applied one level up to gate outcomes themselves.

**Action:** add a `chartable` rate metric to §6.2, reported per stratum (day/night, field-size band, `start_format`) alongside the existing per-stratum accuracy reporting. Add a review trigger if yield differs materially across strata.

### B-4. `official_assumed` has a vacuous-corroboration hole *(1.2.0-introduced)*

M3 DoD (a)(ii) adopts the official winner:

> "…iff the crossing reconstruction contradicts no observed runner and no revision evidence exists"

If the finish is shot head-on or tight and the reconstruction observes **zero** runners, it vacuously contradicts nothing — and `first_past_method = official_assumed` is stamped with no evidence whatsoever.

D-25's entire argument (and Annex A's defence of it) is that the mandatory reconstruction is a *free corroborator*. A reconstruction with no observations is not a corroborator; adopting on it is the "guess dressed as metadata" D-25 exists to forbid.

**Action:** require a minimum evidence bar — e.g. ≥ k observed crossings, or finish-line coverage present for ≥ n seconds before the first crossing — otherwise `first_past_saddle_no = NULL`, EC-12 → `inconclusive` (which the spec already handles cleanly via `anchor_check_status`, leaving Q-3 unaffected).

---

## 3. Sharp findings

### F-1. Cover is defined on a clustered category, so it is discontinuous at an arbitrary boundary

§2.2: X is covered iff ∃ Y **in the same tier** ahead by `[cover_min_sl, cover_max_sl]`.

Tier membership comes from median-linkage clustering at `same_tier_sw = 0.6` plus `tier_hysteresis_s`. A horse sitting slightly off the wheel of the one ahead — a real, common cover position in trot — flips to uncovered the moment its lateral offset crosses the cluster boundary. Cover status therefore inherits every artifact of the clustering.

This matters disproportionately: covered-mask IoU is **30% of the weighted headline score** and one of the two **DoD-1 floors**. The flagship metric depends on a clustering side-effect.

**Proposal (structural — raise now, while no code exists):** define cover directly on geometry, independent of tier:

```
covered(X) ⇔ ∃ Y :  |w_X − w_Y| < cover_lat_sw
                 ∧  (l_Y − l_X) ∈ [cover_min_sl, cover_max_sl]
```

with `cover_lat_sw` a new registry key. Tier remains as-is for state labelling. This decouples the money metric from the cluster boundary and makes cover a continuous geometric predicate.

### F-2. `PARKED` excludes the worst case of the phenomenon it exists to measure

§2.3: `WIDE` = tier ≥ 3 *regardless of cover*. So a horse three-wide with no cover — a heavier aerodynamic and energetic toll than two-wide uncovered — is `WIDE`, not `PARKED`.

D-17 weights `IoU(PARKED)` at 0.5 because "parked-without-cover is the money state." But the metric measures a *label*, not the state. The label's boundary (tier 2 vs tier 3) is orthogonal to the physics the state is a proxy for.

Note the spec already handles cover correctly as a **mask** (covered-mask IoU) rather than a label. Apply the same treatment:

**Proposal:** replace the `IoU(PARKED)` headline component with an **uncovered-outside mask** IoU: `tier ≥ 2 AND covered = false`. The §9 payload already preserves `tier_attr` and `covered` on every geometric state, so nothing is lost and downstream can still recover the exact-label view. DoD-1's floor stops depending on where tier 2 ends.

### F-3. `DETACHED` is a booby trap in the metrics

Three interacting facts:

1. §2.4 / §7.1: `detach_sl = 6.0` SL ≈ 25–30 m. Rare mid-race at Vincennes.
2. §2.4's definition admits only a **single** detached runner at each extreme (rank 1 vs rank 2; last vs second-last). A breakaway *pair* is inexpressible.
3. §6.2 puts `DETACHED` in the headline `rest` set, and its closing paragraph states that if a required DoD/headline component has an empty prediction-and-truth union across the entire evaluation set, **the evaluation is invalid and the golden fixtures MUST be revised**.

A well-behaved 10-race held-out set with no 25 m gaps therefore invalidates its own evaluation and forces a manifest revision — which §6.1 rightly makes expensive.

**Action:** pick one — drop `DETACHED` from `rest`, lower `detach_sl`, or scope the empty-union invalidation rule to DoD-1 components only. Separately, consider whether a detached *group* needs expressing; as written, `DETACHED` will be a very low-prevalence overlay and its downstream feature will be near-constant.

### F-4. DoD-2 is statistically untestable at the specified fixture size

§6.1 requires ≥ 10 observable `BREAK` starts in held-out. §6.3 correctly refuses to let an empty or undersized event set pass by convention — good instinct, wrong stopping point.

At n = 10, the standard error on a recall point estimate is ≈ 0.13. An observed 8/10 is consistent with a true recall anywhere from roughly **0.49 to 0.94**. DoD-2's ≥ 0.80 cannot be certified at this n; it can only be point-estimated.

**Action:** raise the held-out break-start minimum (≥ 25 is a reasonable floor for a 0.80 target) **or** restate DoD-2 honestly as "point estimate ≥ 0.80 with reported confidence interval." The latter is free and matches the spec's general refusal to overclaim.

### F-5. §6.4's identity audit over-counts its own confidence

Two issues with 12 timestamps × 3 runners = 36:

1. **Non-independence.** A tracker ID swap persists across time. Sampling three runners at the same timestamp, and the same runners across nearby timestamps, yields far fewer than 36 independent trials — effective n is closer to the number of distinct tracklet-intervals touched. The audit is therefore more confident than it should be, in the direction that matters (missing a persistent swap).
2. **Operating characteristic is unstated.** "At least 35/36 correct = pass (the smallest integer pass count above 95%)" conflates a per-sample rate with a per-race decision rule. Actual behaviour:

   | True per-sample identity accuracy | P(race passes) |
   |---|---|
   | 0.99 | ≈ 0.95 |
   | 0.98 | ≈ 0.84 |
   | 0.95 | ≈ 0.44 |

**Action:** state the intended operating characteristic explicitly (what accuracy this is designed to reject, with what power), and spread sampled timestamps to reduce clustering — e.g. stratify across the race timeline rather than sampling uniformly at random.

### F-6. DoD-5 will fail across machines as written

§9 mandates **exact IEEE-754 hexadecimal** float representation in the canonical payload, and DoD-5 requires byte-identical re-runs.

The clause "any stochastic inference component fixes and records its RNG seed" does not cover the actual source of nondeterminism in M2: cuDNN autotune, TF32, and non-deterministic atomics produce bit-varying detections across runs, drivers, and hardware — none of which is an RNG-seed problem. Every downstream float (`l_sl`, `w_sw`, `rail_ref_w_sw`, `conf`) inherits that variation, and the strictest possible representation is paired with the least reproducible producer.

**Action — pick one:**

- **(a)** Scope DoD-5 to same-environment re-runs, and require `torch.use_deterministic_algorithms(True)`, `cudnn.benchmark = False`, TF32 disabled, with pinned model weights and driver version recorded under `producer_version`. Acknowledge the throughput cost against M2's 4× real-time soft target.
- **(b)** Quantize floats to a fixed decimal precision in the canonical export before hashing (exact hex remains in operational storage). This makes determinism testable across machines and costs nothing semantically.

(b) is the cheaper path and preserves the spirit of DoD-5.

### F-7. `positions_lost` can report a gain

§2.5: rank immediately after the break end minus rank immediately before the start, "only when both samples have valid order." Rank is computed over **visible** runners (§2.2, pack = visible runners with valid projection).

The spec requires valid order at both samples but not the **same visible set**. If the camera loses the tail while the breaking horse drops back (EC-02 is explicitly in scope here), its rank among visible runners can *improve* while it has in fact lost ground.

**Action:** require an identical visible-runner set at both samples, else NULL; or record `n_visible` at both samples so downstream can filter.

### F-8. Accuracy is measured on a different distribution than the shipped corpus

- DoD-6 and §6.3 void accuracy evaluation on races failing **Q-1 through Q-6**.
- **Q-7** (`over_budget`) is deliberately excluded from that list — but it does set `chartable = false`, which DoD-4 uses to exclude a race from all feature/export views.

So DoD-1 can be satisfied partly on races the production corpus discards. This is probably intentional and defensible (extractor accuracy and operational yield are different questions), but as written it reads like an oversight.

**Action:** one sentence in §6.3 stating the intent, and report the headline score both with and without Q-7 failures.

---

## 4. Smaller items

| # | Item | Where | Action |
|---|---|---|---|
| S-1 | **`first_over` is misnamed.** It is per-frame positional ("furthest-advanced uncovered outside runner right now"), not the harness-racing event sense ("the horse that first left cover to advance"). A horse parked from the start that never challenges still gets `first_over = true`. | §2.3, §11.2 | Rename (`lead_uncovered_outside`) or document the positional sense explicitly. This is precisely the CV↔text semantic drift D-20 exists to prevent, and §11.2 maps « à hauteur de l'animateur » to it in the *positional* sense — so the two readings are already co-existing in one spec. |
| S-2 | **Phases ignore per-runner distance.** D-24 correctly uses the first-past runner's own `distance_run_m` for RK. `t_frac` is race-clock fraction, so in `volte_handicap` the same fraction is a different share of each runner's journey — and `late_phase_start = 0.72` on a 2100 m autostart vs a 2900 m handicap volte are different race positions. | §2.6 | One sentence noting `t_frac` is race-clock, not per-runner course fraction, and that downstream conditions on `base_distance_m` / `distance_run_m`. Consistent with D-22's "the chart records what happened; metadata explains why." |
| S-3 | **M0 rule 4 branch 4 does not assign a status.** "Exactly one field present → use it only if the implied km rate is plausible" — presumably elapsed-only → `direct_elapsed` and km-rate-only → `km_rate_derived`, but rule 5's `official_elapsed_norm_s` derivation depends on which, and it is unstated. | §M0 rule 4 | Name the status in each sub-branch. Newly added normative text; tighten before an agent guesses. |
| S-4 | **Tier clustering span.** The running-median recompute usefully damps chain-linkage (a 0/0.3/0.6/0.9 spread does *not* collapse into one cluster), but tier 1 can still span roughly 2 × `same_tier_sw`. With 14 runners, dense lateral spreads are the normal case. | §2.2 | Add an explicit max cluster span (`max_tier_span_sw`) or a unit test with 14 evenly-spread runners asserting the resulting tier widths. The algorithm is already normative and deterministic — this just bounds it. |
| S-5 | **`plausible_km_rate_min_s = 55` never binds.** Attelé record km rates are ≈ 69 s/km; 55 is below anything physically achievable, so the lower plausibility bound is inert. | §7.1 | Harmless, but tighten to something that can actually fire (e.g. 65) if the check is meant to catch mislabelled units in both directions. |
| S-6 | **Two sources of truth for `split`.** §6.1's versioned golden manifest and `hand_charts.split` both carry dev/held-out membership — the field that enforces held-out sealing (§5.2). | §6.1, §9 | Make the manifest authoritative; treat the column as a denormalized copy validated against it at write time. |
| S-7 | **No abort criteria anywhere.** The spec defines when the project is done; nothing defines when to stop. | new §0.4 or Annex | Add a kill-gate: e.g. after OD-1 + 5 pilot races, if median seeding time > 8 min or M4 tier agreement < 0.85 on hand-labelled frames, reconsider CV against pure hand-charting / text-parse. Cheap insurance against sunk cost, and consistent with D-09's skip-don't-rescue posture. |
| S-8 | **"FROZEN" three times in one day** erodes the word. | Header, §14 | Keep 1.x as DRAFT until OD-1 closes, then freeze once. The changelog discipline itself is excellent and should be kept exactly as is. |

---

## 5. Findings by module

| Module | Findings |
|---|---|
| **M0** | S-3 (branch-4 status), S-5 (`plausible_km_rate_min_s`) |
| **M1** | — (acceptance is well-formed; gated on OD-1 fixture sufficiency, which §M1 already requires) |
| **M2** | F-6 (GPU determinism vs DoD-5) |
| **M3** | B-1 (seeding feasibility untested), B-4 (`official_assumed` vacuous corroboration), F-5 (audit power), §1.3 (`anchor_duration_tolerance_s`) |
| **M4** | F-1 (cover ↔ tier coupling), S-4 (cluster span) |
| **M5** | F-2 (`PARKED` boundary), F-3 (`DETACHED` prevalence) |
| **M6** | F-4 (DoD-2 n=10), F-7 (`positions_lost` visible-set) |
| **M7** | B-2 (DoD-3 vs Q-7), B-3 (no yield floor), F-8 (Q-7 excluded from accuracy voiding) |
| **M8** | F-6 (canonical float representation) |
| **Cross-cutting** | S-1 (`first_over` naming), S-2 (phases vs distance), S-6 (`split` duplication), S-7 (abort criteria), S-8 (freeze discipline) |

---

## 6. Recommended next move

**Skip drill #4. Run OD-1 — as a timed dry run, not a labelling exercise.**

Three replays per the 1.2.0 D-22 stratification (one autostart, one flat volte, one handicap volte). Record:

1. **Seeding time.** Seconds to assign every saddle number from the first stable wide-pan frame, per race, at full field. → falsifies or confirms D-01 and B-1/B-2.
2. **Anchor reproducibility.** Click `t_0` three times on each replay; measure the spread; compare against `anchor_duration_tolerance_s = 2.0`, separately for volte and autostart. → falsifies or confirms EC-12 and §1.3.
3. **Wide-pan coverage.** % of `[t_0, t_end]` in wide pan, and % of the final third. → tests Q-1 (0.65) and Q-2 (0.70) against reality, and gives the first real input to the yield question in B-3.
4. *(Bonus, near-free while the footage is open)* Eyeball whether lateral separations in a 14-runner field look like they resolve at `same_tier_sw = 0.6` SW, and whether 6.0 SL gaps ever occur. → first evidence on F-1 and F-3.

Those numbers falsify or confirm D-01, EC-12, Q-1/Q-2 and the 5-minute budget in a single afternoon. They are also the only numbers in the spec that no amount of further metadata verification can produce.

---

*End of review.*
