#!/usr/bin/env python3
"""Cut spec/SPEC-2.0.0-draft.md from spec/SPEC-1.2.0.md by applying the ledger (SPEC-2.0.0-draft-LEDGER.md)
as exact-substring edits. Every edit must match exactly once; the script fails otherwise, so the
diff base + this file are the complete, reviewable provenance of the draft (D-21, D-36).

usage: python tools/cut_draft.py [--check]   (--check: verify the committed draft equals the cut)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "spec" / "SPEC-1.2.0.md"
DST = ROOT / "spec" / "SPEC-2.0.0-draft.md"

EDITS: list[tuple[str, str, str]] = []   # (ledger id, old, new)


def rep(lid: str, old: str, new: str) -> None:
    EDITS.append((lid, old, new))


# ---------------------------------------------------------------- header / §0 (L-01…L-08)
rep("L-01", "# SPEC-1.2.0 — Vincennes Attelé Trip-State Extraction Pipeline",
    "# SPEC-2.0.0-draft — Vincennes Attelé Trip-State Extraction Pipeline")
rep("L-01", "**Status:** FROZEN (normative). Changes require a version bump per §14.\n**Version:** 1.2.0",
    "**Status:** DRAFT (D-36). Not normative for golden charting or calibration. Agents MAY build M0, schema migrations and tooling scaffolds against it; golden charting (OD-3), calibration (§7) and M2 training MUST NOT begin. Every value marked `[EG: …]` is provisional until `registers/evidence_gated.yaml` instantiates it.\n"
    "**Promotion rule (D-36):** this file becomes `SPEC-2.0.0.md`, Status FROZEN, in one commit when (1) every `[EG]` entry is instantiated, (2) every kill-gate in §0.4 passes, (3) D-26…D-36 are appended to §1, (4) `tools/freeze_check.py` exits 0.\n"
    "**Version:** 2.0.0-draft — diff base SPEC-1.2.0 (last FROZEN 1.x); edit ledger `SPEC-2.0.0-draft-LEDGER.md`; cut by `tools/cut_draft.py`. MAJOR because D-17 is reopened (headline re-cut, D-27), a D-08-frozen core definition changes (cover, D-26) and a payload field is renamed (`first_over` → `lead_uncovered_outside`).")
rep("L-02", "| DoD-1 | On the held-out golden set (§6), both `IoU(PARKED)` and covered-mask IoU (`covered = true`, §6.2–6.3) are **≥ 0.85**. |",
    "| DoD-1 | On the held-out golden set (§6), both the **uncovered-outside mask IoU** (`tier ≥ 2 ∧ covered = false`, §6.2) and the **covered-mask IoU** (`covered = true`, §6.2–6.3) are **≥ 0.85**. The `PARKED` label is no longer a floor (D-27). |")
rep("L-03", "pre-review break-candidate recall vs. hand charts is **≥ 0.80**; final `BREAK` events require human acceptance.",
    "pre-review break-candidate recall vs. hand charts has a **point estimate ≥ 0.80**, reported with its Wilson 95% confidence interval — at the §6.1 fixture size this is a point estimate, not a certification (D-31); final `BREAK` events require human acceptance.")
rep("L-04", "including attempts later excluded as `over_budget`, is **≤ 5 minutes**, measured over ≥ 20 consecutive eligible attempts. |",
    "including attempts later excluded as `over_budget`, is **≤ 5 minutes** `[EG: pilot → dod3_median_target_min]`, measured over ≥ 20 consecutive eligible attempts. The operational cap is Q-7's `human_budget_cap_min`, not this target (D-29). |")
rep("L-05", "Re-running the pipeline on the same inputs reproduces an identical canonical data payload (§M8), excluding operational timestamps. |",
    "Re-running the pipeline on the same inputs reproduces an identical **quantized canonical** data payload (§9, D-32), excluding operational timestamps. |")
rep("L-06", "| OD-1 | 3 sample Equidia Vincennes replays pulled and inspected (shot composition, % wide-pan, resolution/fps, full-race coverage). The sample set SHOULD span start formats: one autostart, one flat volte, one handicap volte (D-22). | Freezing M1 shot-type classes; golden fixture selection (§6.1). | Project owner |",
    "| OD-1x | Timed dry run on 3 sample replays (one autostart, one flat volte, one handicap volte, D-22; pistes per DR-06) per `protocols/OD-1x/PROTOCOL.md`: timed seeding, anchor reproducibility and bias per start type, wide-pan coverage, geometry eyeball incl. lateral scale, finish-shot crossing evidence, recall scan. Supersedes OD-1. | Instantiating every `[EG]` value (§7.1, `registers/evidence_gated.yaml`); freezing M1 shot-type classes; golden fixture selection (§6.1); the 2.0.0 freeze (D-36). | Project owner |")
rep("L-06", "Until OD-1 resolves, all camera/shot assumptions in this spec are **provisional-normative**",
    "Until OD-1x resolves, all camera/shot assumptions in this spec are **provisional-normative**")
rep("L-07", "Until OD-1x resolves, all camera/shot assumptions in this spec are **provisional-normative**: agents MUST build against them but MUST NOT hard-code them beyond the config layer.\n",
    "Until OD-1x resolves, all camera/shot assumptions in this spec are **provisional-normative**: agents MUST build against them but MUST NOT hard-code them beyond the config layer.\n\n"
    "### 0.4 Kill-gates (normative structure; values `[EG]`; D-33)\n\n"
    "The project defines when to stop, not only when it is done. Evaluated after OD-1x and a 5-race pilot; machine copy in `registers/kill_gates.yaml`.\n\n"
    "| ID | Gate | On trigger |\n|----|------|------------|\n"
    "| KG-1 | Median seeding time (first stable wide-pan frame → all saddle numbers assigned) > 8 min `[EG]` | Stop; reconsider CV against pure hand-charting / text-parse |\n"
    "| KG-2 | M4 tier agreement < 0.85 on pilot hand-labelled frames | Recalibrate once; still failing → stop |\n"
    "| KG-3 | Pilot `chartable` yield < 40 % | Gate review before any further charting |\n"
    "| KG-4 | Post-offset anchor residual spread > 2 × provisional tolerance on either start type | EC-12 design review before freeze |\n\n"
    "**Pilot exemption (normative).** The 5-race pilot runs on a throwaway stack that is exempt from gates G-1…G-3 (§4.0). Its outputs carry `producer_kind = pilot_throwaway`, are evidence for the freeze only, and MUST NOT enter the corpus, the golden set or calibration. The pilot's 5 races and the 3 OD-1x replays MAY later be dev races but MUST NOT be held-out races.\n")
rep("L-09", "| D-25 | First-past resolution ladder: directly observed crossing > official winner corroborated by the mandatory crossing reconstruction (`official_assumed`) > human adjudication. `arrival_revised = false` requires an authoritative source or adjudication and MUST NOT be a default; absence of a revision field is not evidence of no revision. | The cheapest honest corroborator is a check M3 already runs. |\n",
    "| D-25 | First-past resolution ladder: directly observed crossing > official winner corroborated by the mandatory crossing reconstruction (`official_assumed`) > human adjudication. `arrival_revised = false` requires an authoritative source or adjudication and MUST NOT be a default; absence of a revision field is not evidence of no revision. | The cheapest honest corroborator is a check M3 already runs. |\n\n"
    "**Pending at freeze (D-36):** D-26…D-36 are defined in `decisions/DECISION-LOG.md` and are the agreed direction of this draft; the promotion commit appends them to this table verbatim. They MAY be built against; they MUST NOT be reopened by agents.\n")

# ---------------------------------------------------------------- §2 (L-10…L-17)
rep("L-12", "when it affects only which PARKED runner is `first_over`, both retain `PARKED` and use the nullable ambiguity rule in §2.3.",
    "when it affects only which PARKED runner is `lead_uncovered_outside`, both retain `PARKED` and use the nullable ambiguity rule in §2.3.")
rep("L-10", "The strict clustering `<` boundary, closed attachment boundary and median-linkage algorithm are normative.",
    "The strict clustering `<` boundary, closed attachment boundary and median-linkage algorithm are normative. After clustering, any occupied cluster whose lateral span (max − min `w_sw`) exceeds `max_tier_span_sw` (default 1.2 SW `[EG: OD-1x]`) splits recursively at its largest internal gap (ties → the lower-index gap); the bound and the split rule are normative and a unit test with 14 evenly spread runners is part of M4 acceptance (D-26).")
rep("L-11", "- **Cover**: runner X is **covered** iff ∃ runner Y in the same tier with Y longitudinally ahead of X by the closed interval `[cover_min_sl, cover_max_sl]` (defaults **[0.3, 2.0] SL**).",
    "- **Cover** (tier-independent, D-26): runner X is **covered** iff ∃ valid runner Y with `(l_Y − l_X) ∈ [cover_min_sl, cover_max_sl]` (closed; defaults **[0.3, 2.0] SL**) and `\\|w_X − w_Y\\| < cover_lat_sw` (default **0.8 SW** `[EG: OD-1x]`). Tier membership plays no role: tiers label states, geometry decides cover. The §3.4 minimum-duration smoothing applies to the cover predicate before classification.")
rep("L-12", "| `PARKED` | Tier 2, **not** covered. `first_over = true` for the uniquely furthest-advanced PARKED runner. If the top PARKED order is ambiguous under `rank_tie_sl`, all tied runners use `first_over = NULL` and `first_over_ambiguous = true`. At most one runner holds `first_over = true` per frame. | « à l'extérieur sans abri » / first-over |",
    "| `PARKED` | Tier 2, **not** covered. `lead_uncovered_outside = true` for the uniquely furthest-advanced PARKED runner (positional sense: the parked runner furthest up the field *at this frame*; the move-detection event \"first over\" is out of scope, §12). If the top PARKED order is ambiguous under `rank_tie_sl`, all tied runners use `lead_uncovered_outside = NULL` and `lead_uncovered_outside_ambiguous = true`. At most one runner holds `lead_uncovered_outside = true` per frame. | « à l'extérieur sans abri » / « à hauteur de l'animateur » |")
rep("L-13", "**Design invariant (normative):** `LEADER` and `PARKED` are both uncovered but MUST remain distinct states",
    "**Metric note (normative, D-27):** the headline metric (§6.2) measures the uncovered-outside *mask* (`tier ≥ 2 ∧ covered = false`), not the `PARKED` label; the label boundary (tier 2 vs ≥ 3) is categorical by design while the money metric is geometric. `[OPEN: RP-11]` Under tier-independent cover a tier-1 runner with no tier-1 runner ahead can be covered by an outside runner; this table has no row for it and implementations emit `UNKNOWN` with reason `table_gap_tier1_lead_covered` until the owner decides (recommended: keep `LEADER`, record `covered = true`).\n\n"
    "**Design invariant (normative):** `LEADER` and `PARKED` are both uncovered but MUST remain distinct states")
rep("L-14", "In `start_format = volte_handicap` races, rear detachment near `t_0` is structurally induced by rendements: it is recorded unchanged and conditioned on `rendement_m` downstream (D-22). |",
    "In `start_format = volte_handicap` races, rear detachment near `t_0` is structurally induced by rendements: it is recorded unchanged and conditioned on `rendement_m` downstream (D-22). `DETACHED` is diagnostic in evaluation (D-28): excluded from the headline `rest` set, reported descriptively per stratum; detached *groups* (breakaway pairs) are out of scope (§12). |")
rep("L-15", "nullable `positions_lost` (rank immediately after the end minus rank immediately before the start, only when both samples have valid order; positive means places lost)",
    "nullable `positions_lost` (rank immediately after the end minus rank immediately before the start, valid only when both samples have valid order **and the visible-runner set is identical at both samples**, else NULL; positive means places lost; `positions_lost_basis_n` records the size of that visible set — D-31)")
rep("L-16", "Event boundaries are reviewable outputs, not uneditable detector proposals.",
    "Event boundaries are reviewable outputs, not uneditable detector proposals. A break still open at `t_frac = 1.0` keeps `t_end_frac = NULL` and `recovered = NULL`; this is expected to coincide with a DAI and agents MUST NOT \"fix\" it (DR-10).")
rep("L-10b", "4. Orient the axis as `u_long` using persisted `travel_direction_sign ∈ {-1, +1}` relative to that canonical vector.",
    "4. Orient the axis as `u_long` using persisted `travel_direction_sign ∈ {-1, +1}` relative to that canonical vector. The unsigned axis MUST be temporally smoothed across frames (`axis_smooth_s`) and estimated from displacements longer than `axis_min_vector_sl`·SL with length weighting: lateral coordinates are extremely sensitive to axis error — a tilt δ displaces a runner `l` SL back by ≈ `(SL/SW)·l·sin δ` SW, so with `sw_ratio = 0.35` a 5 SL pack needs ≈ 1° axis accuracy for `same_tier_sw = 0.6` to separate lanes (RP-21). A single frame's motion estimate MUST NOT set the axis on its own.")
rep("L-11b", "- Y-coordinate-as-depth heuristics: **banned** (superseded by pack-space projection).",
    "- Y-coordinate-as-depth heuristics: **banned** (superseded by pack-space projection).\n\n"
    "`[OPEN: RP-19/RP-22/RP-23 — owner decision]` The world-space simulator study (`docs/research/11-simulated-geometry.md`) shows that from an elevated side-on camera lateral metres project at roughly height/depth of longitudinal metres, so `SW = SL·sw_ratio` merges adjacent lanes by construction, that the §3.1 motion axis is biased by pan/zoom even without jitter, and that the `(mid-x, max-y)` centroid carries a pan-dependent lateral bias. Three options are implemented in the reference projector and proposed for adoption: (a) `axis_source = rail` — the projected rail-line direction as the primary axis, never smoothed; (b) `lateral_scale_mode = rail_fence_projective` — a 1-D projective lateral coordinate from the rail line, the fence line and their vanishing point (horizon assumed horizontal; needs `track_width_sl` `[EG]`), with each runner measured against the nearest rail/fence polyline segment on bends; (c) a foot-point correction (`vehicle_half_width_sw`) from the bbox bottom edge to the vehicle centre line. (b) is not a homography to track coordinates and would need an explicit carve-out in this section. Lateral resolvability remains bounded by the covering camera's elevation per track section (RP-24).")
rep("L-17", "CV/human chart rows are emitted only for `t_frac ∈ [0, 1]`; stored fractions are clamped only for floating-point epsilon, never to rescue a materially out-of-anchor timestamp.",
    "CV/human chart rows are emitted only for `t_frac ∈ [0, 1]`; stored fractions are clamped only for floating-point epsilon, never to rescue a materially out-of-anchor timestamp.\n\n"
    "`t_frac` is a **race-clock** fraction, not a per-runner course fraction: in `volte_handicap` races the same fraction is a different share of each runner's journey, and `late_phase_start` on a 2100 m autostart and a 2900 m handicap volte are different track positions. Downstream conditions on `base_distance_m`, `distance_run_m` and `piste`. Track-landmark detection stays banned; approximate track position is reconstructible downstream from `piste`, distance and RK (S-2, DR-07).")
rep("L-12", "- Derived attributes are recomputed after smoothing. In particular, at most one co-timed `PARKED` segment may have `first_over = true`.",
    "- Derived attributes are recomputed after smoothing. In particular, at most one co-timed `PARKED` segment may have `lead_uncovered_outside = true`.")

# ---------------------------------------------------------------- §4 (L-18…L-26)
rep("L-20", "race metadata record (`race_id`, date, meeting, race no., `base_distance_m`, `start_type ∈ {volte, autostart}`, `start_format ∈ {autostart, volte_flat, volte_handicap}`, declared runners with saddle numbers and per-runner `distance_run_m`,",
    "race metadata record (`race_id`, date, meeting, race no., `base_distance_m`, `start_type ∈ {volte, autostart}`, `start_format ∈ {autostart, volte_flat, volte_handicap}`, `piste ∈ {GP, PP}` (from ingest, never inferred from distance — DR-06), declared runners with saddle numbers, per-runner `distance_run_m` and `autostart_row ∈ {1, 2, NULL}` (DR-04),")
rep("L-18", "   - exactly one field present → use it only if the implied km rate `elapsed × 1000 / distance_run_m` (resp. `km_rate` directly) lies in `[plausible_km_rate_min_s, plausible_km_rate_max_s]`, else `unavailable` with `elapsed_implausible` / `km_rate_implausible`;",
    "   - exactly one field present → use it only if the implied km rate `elapsed × 1000 / distance_run_m` (resp. `km_rate` directly) lies in `[plausible_km_rate_min_s, plausible_km_rate_max_s]`: elapsed-only and plausible → `direct_elapsed`; km-rate-only and plausible → `km_rate_derived` (S-3); else `unavailable` with `elapsed_implausible` / `km_rate_implausible`;")
rep("L-21", "(ii) otherwise the official winner is adopted iff the crossing reconstruction contradicts no observed runner and no revision evidence exists — `official_unrevised` when `arrival_revised = false` (authoritative source), `official_assumed` when `arrival_revised` is NULL (zero extra operator cost; the mandatory reconstruction is the corroborator);",
    "(ii) otherwise the official winner is adopted iff the crossing reconstruction observes **≥ `finish_evidence_min_k` crossings** (default 3 `[EG: OD-1x]`), all consistent with the reference order, and no revision evidence exists — `official_unrevised` when `arrival_revised = false` (authoritative source), `official_assumed` when `arrival_revised` is NULL (zero extra operator cost; the mandatory reconstruction is the corroborator); zero or insufficient observed crossings → `first_past_saddle_no = NULL` and EC-12 `inconclusive` — a corroborator with no observations is not a corroborator (D-30); `race_anchors.finish_evidence_n` records the count;")
rep("L-21", "`first_past_method` MUST resolve via `observed_crossing` or `human_confirm`, never `official_assumed`. |",
    "`first_past_method` MUST resolve via `observed_crossing` or `human_confirm`, never `official_assumed`. A second synthetic fixture (head-on finish, zero observed crossings, no revision evidence) MUST resolve `first_past_saddle_no = NULL` with `anchor_check_status = inconclusive`, never `official_assumed` (D-30). |")
rep("L-22", "Compare the initial visible lineup against start structure: official autostart lanes, or volte rendement **bands at their marks**",
    "Compare the initial visible lineup against start structure: official autostart lanes — for fields > 9 the autostart is modelled as two rows: front-row lateral order = post order, second row checked for presence only, never order (DR-04) — or volte rendement **bands at their marks**")
rep("L-24", "Keyboard-driven frame-stepper (CLI + OpenCV window grade, D-16): play/pause/step, click-runner→type-saddle-number, jump-to-next-flagged-cut,",
    "Keyboard-driven frame-stepper (CLI + OpenCV window grade, D-16): play/pause/step, configurable **≥ 2× auto-play with automatic slowdown at flagged events** (DR-12), click-runner→type-saddle-number, jump-to-next-flagged-cut, a \"possible recall\" flag surfaced when EC-14 heuristics fire,")
rep("L-25", "with `state_kind ∈ {base, overlay}`, `covered`, `confidence`, `visibility`, `start_truncated` and `end_truncated`. `BREAKING` is appended by M6 after confirmation. |",
    "with `state_kind ∈ {base, overlay}`, `covered`, `lead_uncovered_outside`, `lead_uncovered_outside_ambiguous`, `confidence`, `visibility`, `start_truncated` and `end_truncated`. `BREAKING` is appended by M6 after confirmation. |")
rep("L-25", "| **Acceptance** | On dev hand charts: macro base-state segment IoU ≥ 0.80; both `IoU(PARKED)` and covered-mask IoU ≥ 0.85 (definitions §6.2–6.3; pre-calibration targets, final numbers via §7). |",
    "| **Acceptance** | On dev hand charts: macro base-state segment IoU ≥ 0.80; both the uncovered-outside mask IoU and the covered-mask IoU ≥ 0.85 (definitions §6.2–6.3; pre-calibration targets, final numbers via §7). |")
rep("L-26", "DAI cross-check: officially sanctioned DAI runners SHOULD have ≥ 1 candidate — misses logged as `dai_uncaught` for calibration.",
    "DAI cross-check: officially sanctioned DAI runners SHOULD have ≥ 1 candidate — misses logged as `dai_uncaught_break_expected`, or as `dai_gait_other` when the sanction concerned another gait (amble / traquenard; human tag at review); §7 calibration MUST NOT tune break thresholds against `dai_gait_other` (DR-09).")

# ---------------------------------------------------------------- §5 (L-27, L-28)
rep("L-27", "### 5.1 Per-race operator loop (target ≤ 5 min, D-09)", "### 5.1 Per-race operator loop (target median ≤ 5 min, cap 8 min `[EG]`; D-09, D-29)")
rep("L-27", "4. Tool auto-plays; pauses at flagged cuts / tracker-confidence drops",
    "4. Tool auto-plays at ≥ 2× with automatic slowdown at flagged events (DR-12); pauses at flagged cuts / tracker-confidence drops")
rep("L-27", "**Budget rule:** wall-clock over 5 min → race flagged `over_budget` and `chartable = false`;",
    "**Budget rule:** wall-clock over `human_budget_cap_min` (8 min `[EG: ≈ p90 of pilot]`, D-29) → race flagged `over_budget` and `chartable = false`;")
rep("L-28", "- Dev/held-out split (30/10) is fixed in the golden manifest before charting.",
    "- Dev/held-out split (30/10) is fixed in the golden manifest before charting. The manifest is authoritative for `split`; `hand_charts.split` is a denormalized copy validated at write time, and a mismatch rejects the write (S-6).")

# ---------------------------------------------------------------- §6 (L-28…L-33)
rep("L-28", "The manifest records `start_format` per race; ≥ 5 dev and ≥ 2 held-out races MUST be `volte_handicap`.",
    "The manifest records `start_format` and `piste` per race; ≥ 5 dev and ≥ 2 held-out races MUST be `volte_handicap`; held-out SHOULD cover both pistes and both day/night strata present in the candidate pool.")
rep("L-29", "| **Weighted headline score** | `0.5·IoU(PARKED) + 0.3·IoU(covered=true) + 0.2·MacroIoU(rest)`, where `rest = {LEADER, RAIL_UNCOVERED, WIDE, DETACHED}` and `DETACHED` uses overlay Segment IoU. This is the number quoted as \"extractor accuracy\"; DoD-1 additionally requires the two component floors stated there. |",
    "| **Uncovered-outside mask IoU** | Same construction as the covered mask over `tier ≥ 2 ∧ covered = false` (`PARKED`, and `WIDE` with `covered = false`). The money mask (D-27). |\n"
    "| **Weighted headline score** | `0.5·IoU(uncovered-outside mask) + 0.3·IoU(covered mask) + 0.2·MacroIoU(rest)`, where `rest = {LEADER, RAIL_UNCOVERED, WIDE}`; `DETACHED` is reported descriptively per stratum, outside the headline (D-28). Reported both with and without Q-7 failures (D-35). This is the number quoted as \"extractor accuracy\"; DoD-1 additionally requires the two mask floors stated there. |\n"
    "| **Chartable rate (per stratum)** | Share of eligible attempts with `chartable = true`, overall and per stratum (day/night × field-size band × `start_format` × `piste`). Review trigger: any stratum below `stratum_yield_review_factor` × overall (0.5 `[EG]`) → manifest/threshold review before further charting (D-35). |\n"
    "| **Segmental edit score, F1@{10, 25, 50}** (descriptive) | Lea et al. (2017) conventions over per-runner base-state sequences; reported next to Segment IoU to expose over-segmentation. Never a floor. |")
rep("L-30", "If a required DoD/headline component has an empty union across the entire evaluation set, the evaluation is invalid and the golden fixtures MUST be revised.",
    "If a **DoD-1 component** (either mask IoU) has an empty union across the entire evaluation set, the evaluation is invalid and the golden fixtures MUST be revised; any other component is simply omitted for that set (D-28).")
rep("L-32", "- Per-stratum reporting REQUIRED: day vs. night, field size bands (≤ 10, 11–14).",
    "- Per-stratum reporting REQUIRED: day vs. night, field size bands (≤ 10, 11–14), `start_format`, `piste`.\n"
    "- Q-7 (`over_budget`) is deliberately excluded from the accuracy-voiding list: extractor accuracy and operational yield are different questions. The headline is therefore reported both with and without Q-7 failures (F-8, D-35). DoD-2 is reported as a point estimate with its Wilson 95% interval (D-31).")
rep("L-33", "Per audited race: sample 12 random timestamps × 3 random visible runners without replacement where possible; human verifies saddle-number correctness in the tool. The RNG seed (`SHA-256(race_id | extractor_version | \"identity-audit-v1\")`) and sampled coordinates are persisted. At least 35/36 correct = pass (the smallest integer pass count above 95%). The pooled exact rate and per-race counts MUST be reported; this is a sampled identity estimate, not a claim that every unsampled frame was inspected.",
    "Per audited race: sample 12 timestamps **stratified across 4 equal phase bins of `[t_0, t_end]`** (3 per bin), and at each timestamp 3 visible runners resampled without replacement where possible; human verifies saddle-number correctness in the tool. The RNG seed (`SHA-256(race_id | extractor_version | \"identity-audit-v1\")`) and sampled coordinates are persisted. At least 35/36 correct = pass. The sampled points MUST touch ≥ 8 distinct tracklet intervals, otherwise the audit reports its effective n (identity errors persist along a tracklet, so 36 samples are far fewer than 36 independent trials). **Operating characteristic (informative):** under independence the rule accepts a race with 0.99 per-sample identity accuracy w.p. ≈ 0.95, 0.98 w.p. ≈ 0.84 and 0.95 w.p. ≈ 0.46 — the audit is a smoke test, not a certificate (D-31). The pooled exact rate and per-race counts MUST be reported; this is a sampled identity estimate, not a claim that every unsampled frame was inspected.")

# ---------------------------------------------------------------- §7 (L-19, L-34)
rep("L-34", "| `normalized_fps` | 25.0 (provisional until OD-1) | M0 |", "| `normalized_fps` | 25.0 `[EG: OD-1x]` | M0 |")
rep("L-34", "| `same_tier_sw` | 0.6 | §2.2 |",
    "| `same_tier_sw` | 0.6 `[EG: OD-1x sanity]` | §2.2 |\n| `max_tier_span_sw` | 1.2 `[EG: OD-1x]` | §2.2 (D-26) |\n| `rail_ref_conf_min` | 0.5 | EC-13 (M4 rail-reference confidence; module default) |\n| `axis_neighbourhood_k` | 0 `[EG: OD-1x bend frame]` | §3.1 (0 = whole-pack axis; RP-20) |\n| `axis_min_vector_sl` / `axis_smooth_s` | 0.05 / 1.0 | §3.1 motion-axis jitter guard and temporal smoothing (RP-21) |\n| `lateral_scale_mode` / `track_width_sl` | sw_ratio / 5.8 `[EG: track plan]` | §3.2 lateral scale; `rail_fence` = two track lines at known separation (RP-19, `[OPEN]`) |")
rep("L-34", "| `cover_min_sl` / `cover_max_sl` | 0.3 / 2.0 | §2.2 |",
    "| `cover_min_sl` / `cover_max_sl` | 0.3 / 2.0 | §2.2 |\n| `cover_lat_sw` | 0.8 `[EG: OD-1x]` | §2.2 (D-26) |")
rep("L-34", "| `anchor_duration_tolerance_s` | 2.0 | EC-12 / Q-3 |",
    "| `anchor_offset_volte_s` / `anchor_offset_autostart_s` | 0.0 / 0.0 `[EG: OD-1x]` | EC-12 (D-34) |\n| `anchor_tol_volte_s` / `anchor_tol_autostart_s` | 2.0 / 2.0 `[EG: OD-1x]` | EC-12 / Q-3 (D-34) |\n| `finish_evidence_min_k` | 3 `[EG: OD-1x]` | M3 DoD (a) rung (ii) (D-30) |\n| `human_budget_cap_min` | 8 `[EG: pilot ≈ p90]` | §5.1 / Q-7 (D-29) |\n| `stratum_yield_review_factor` | 0.5 `[EG]` | §6.2 chartable rate (D-35) |")
rep("L-19", "| `plausible_km_rate_min_s` / `plausible_km_rate_max_s` | 55 / 110 | M0 metadata normalization |",
    "| `plausible_km_rate_min_s` / `plausible_km_rate_max_s` | 65 / 110 | M0 metadata normalization (S-5: 55 never bound; attelé record RK ≈ 69 s/km) |")
rep("L-34", "This table is the mandatory minimum registry, not permission for hidden module constants.",
    "Machine copy: `config/thresholds/TS-0.0.0-provisional.yaml` (module namespaces `m1_shots`, `m2_detect`, `m3_track`, `m6_events` hold module defaults, tuned in §7.2). This table is the mandatory minimum registry, not permission for hidden module constants.")

# ---------------------------------------------------------------- §8 (L-35, L-36)
rep("L-35", "| EC-12 | Timeline-anchor duration disagrees with the first-past runner's normalized official time | `abs((tend_video_s - t0_video_s) - official_elapsed_norm_s(first_past)) > anchor_duration_tolerance_s`, where",
    "| EC-12 | Timeline-anchor duration disagrees with the first-past runner's normalized official time | `abs((tend_video_s - t0_video_s) - official_elapsed_norm_s(first_past) - anchor_offset_<start_type>_s) > anchor_tol_<start_type>_s` (per-start-type bias offset and tolerance, D-34; all four keys `[EG: OD-1x]`), where")
rep("L-36", "| EC-13 | Rail lane empty or rail reference unreliable | Rail-reference confidence below its namespaced M4 threshold, or innermost occupied-cluster center > `rail_attach_sw` from `rail_ref_w_sw + rail_lane_center_offset_sw` | Preserve relative cluster IDs for diagnostics but emit absolute `tier = NULL`, `conf = 0` and downstream `UNKNOWN`; never promote the innermost occupied cluster to tier 1 | `pct_rail_reference_valid` |",
    "| EC-13 | Rail lane empty or rail reference unreliable | Rail-reference confidence below `rail_ref_conf_min`, or innermost occupied-cluster center > `rail_attach_sw` from `rail_ref_w_sw + rail_lane_center_offset_sw` | Preserve relative cluster IDs for diagnostics but emit absolute `tier = NULL`, `conf = 0` and downstream `UNKNOWN`; never promote the innermost occupied cluster to tier 1 | `pct_rail_reference_valid` |\n"
    "| EC-14 | Faux départ / volte recall (aborted start, restart) | Post-release deceleration or turn-back of the pack; restart footage; commentary cue noted by the operator | `t_0` MUST anchor the **final** release; the tool surfaces a \"possible recall\" flag and MUST NOT auto-correct; the first release's timecode MAY be logged for diagnostics (DR-03) | `recall_suspected` |")

# ---------------------------------------------------------------- §9 (L-37…L-40)
rep("L-38", "| `races` | `race_id` | Date, meeting, race no., `base_distance_m`, `start_type`, `start_format`, `start_handicap`,",
    "| `races` | `race_id` | Date, meeting, race no., `base_distance_m`, `start_type`, `start_format`, `start_handicap`, `piste ∈ {GP, PP}` (DR-06),")
rep("L-38", "| `runners` | `race_id, saddle_no` | Driver, horse, post/volte band, `distance_run_m`, `rendement_m`,",
    "| `runners` | `race_id, saddle_no` | Driver, horse, post/volte band, `autostart_row ∈ {1, 2, NULL}` (DR-04), `distance_run_m`, `rendement_m`,")
rep("L-38", "nullable `first_past_method ∈ {official_unrevised, official_assumed, observed_crossing, human_confirm}`, `official_time_method",
    "nullable `first_past_method ∈ {official_unrevised, official_assumed, observed_crossing, human_confirm}`, `finish_evidence_n` (D-30), `recall_suspected` (EC-14), `official_time_method")
rep("L-37", "| `state_segments` | `race_id, saddle_no, seg_id` | `state_kind`, `state`, `covered`, `first_over`, `first_over_ambiguous`, `tier_attr`,",
    "| `state_segments` | `race_id, saddle_no, seg_id` | `state_kind`, `state`, `covered`, `lead_uncovered_outside`, `lead_uncovered_outside_ambiguous`, `tier_attr`,")
rep("L-38", "| `events` | `race_id, saddle_no, event_id` | `type`, attributes per §2.5, `method`, `review_status`, `human_confirmed`, `reviewed_at` |",
    "| `events` | `race_id, saddle_no, event_id` | `type`, attributes per §2.5 incl. `positions_lost_basis_n`, `dai_tag ∈ {dai_uncaught_break_expected, dai_gait_other, NULL}`, `method`, `review_status`, `human_confirmed`, `reviewed_at`; race-level `SHOT_GAP` rows use `saddle_no = 0` |")
rep("L-38", "| `qc` | `race_id` | Race-level §M7 fields: `chartable`, failure codes, wide-pan coverage, human-minutes, stratum, `finish_check_status`, `finish_check_basis`, `start_check_status`, `anchor_check_status`, `id_suspect` |",
    "| `qc` | `race_id` | Race-level §M7 fields: `chartable`, failure codes, wide-pan coverage, human-minutes, stratum, `finish_check_status`, `finish_check_basis`, `start_check_status`, `anchor_check_status`, `id_suspect`, `realization` (DR-11 coverage-failure tag), `recall_suspected` (EC-14) |")
rep("L-40", "| `versions` | `producer_version` | `producer_kind ∈ {cv_extract, human_chart, text_parse, config}`,",
    "| `versions` | `producer_version` | `producer_kind ∈ {cv_extract, human_chart, text_parse, config, pilot_throwaway}` (§0.4), `determinism_env` (D-32),")
rep("L-37", "`first_over` is false on known non-`PARKED` geometric states, boolean on unambiguous `PARKED`, and NULL on `NOT_VISIBLE`, `UNKNOWN` or an ambiguous top-`PARKED` tie. `first_over_ambiguous` is true only for that tie,",
    "`lead_uncovered_outside` is false on known non-`PARKED` geometric states, boolean on unambiguous `PARKED`, and NULL on `NOT_VISIBLE`, `UNKNOWN` or an ambiguous top-`PARKED` tie. `lead_uncovered_outside_ambiguous` is true only for that tie,")
rep("L-39", "NULL/booleans use JSON literals, and finite floats use an exact IEEE-754 hexadecimal string. NaN and infinities are forbidden; unavailable numeric values use NULL.",
    "NULL/booleans use JSON literals, and finite floats are **quantized to fixed decimals before hashing** (race fractions 6 dp; seconds 3 dp; SL/SW/confidence 4 dp) and serialized as decimal strings — exact IEEE-754 hex is dropped from the canonical payload and operational storage is unconstrained; quantization applies to the export only, never inside comparisons or threshold logic (D-32). NaN and infinities are forbidden; unavailable numeric values use NULL.")
rep("L-39", "Any stochastic inference component fixes and records its RNG seed and deterministic-runtime settings under `producer_version`.",
    "Any stochastic inference component fixes and records its RNG seed and deterministic-runtime settings under `producer_version.determinism_env`: framework/CUDA/cuDNN/driver versions, GPU model and count, `use_deterministic_algorithms`, `cudnn.benchmark`, `cudnn.deterministic`, TF32 flags, `CUBLAS_WORKSPACE_CONFIG`, seed, half-precision flag, batch size, model-weight hashes. Bit-identity across machines is NOT required (D-32); same-environment bit-identity of unquantized sidecars is an optional CI check.")

# ---------------------------------------------------------------- §10 (L-41)
rep("L-41", "| Q-7 | Human budget respected (`human_minutes ≤ 5`); `over_budget` is not waivable in v1 (D-09) |",
    "| Q-7 | Human budget respected (`human_minutes ≤ human_budget_cap_min`, 8 min `[EG: pilot ≈ p90]`); `over_budget` is not waivable in v1 (D-09, D-29) |")

# ---------------------------------------------------------------- §11 (L-42, L-43)
rep("L-42", "| `PARKED` / `first_over` | `[C]` « nez au vent »;", "| `PARKED` / `lead_uncovered_outside` | `[C]` « nez au vent »;")
rep("L-42", "`first_over = true` additionally requires explicit proximity to the leader, e.g. « à hauteur / côté / dehors de l'animateur ».",
    "`lead_uncovered_outside = true` (positional sense, §2.3 — not the move-detection event) additionally requires explicit proximity to the leader, e.g. « à hauteur / côté / dehors de l'animateur ».")
rep("L-43", "8. Text-derived `BREAK` events enter with `review_status = pending` and `human_confirmed = false` until reviewed under the M3/M6 confirmation loop. Phase-level text charts MUST be evaluated separately from exact-fraction CV charts.",
    "8. Text-derived `BREAK` events enter with `review_status = pending` and `human_confirmed = false` until reviewed under the M3/M6 confirmation loop. Phase-level text charts MUST be evaluated separately from exact-fraction CV charts.\n\n"
    "### 11.4 Phase vocabulary (shape normative; entries `[C]`-gated — DR-08)\n\n"
    "Phase phrases map to `phase ∈ {early, mid, late, stretch, unknown}` under the same `[C]` evidence rules as states (§11.1). Entries below are the attested families to be confirmed with corpus provenance before text parsing activates; unattested entries MUST NOT be used.\n\n"
    "| Phrase family | Phase | Notes |\n|---|---|---|\n"
    "| « dès le départ », « au départ », « dans les premiers mètres » | early | — |\n"
    "| « à mi-parcours », « à mi-course » | mid | — |\n"
    "| « dans le dernier tournant », « à l'entrée de la ligne droite », « dans la montée » | late | « la montée » is Vincennes-specific (grande piste) |\n"
    "| « dans la ligne droite », « sur le poteau », « au poteau » | stretch | semantic subphase of late; never converted to a fraction |\n"
    "| « en fin de course », « sur la fin » | late | ambiguous late/stretch → `late` |")

# ---------------------------------------------------------------- §12 (L-44)
rep("L-44", "| Text-comment parsing into the schema | Out of this spec's build | Parallel workstream; writes `hand_charts`-shaped data per §11 rules |",
    "| Text-comment parsing into the schema | Out of this spec's build | Parallel workstream; writes `hand_charts`-shaped data per §11 rules |\n"
    "| Detached groups (breakaway pairs) | Deferred | v1.5 (D-28) |\n"
    "| Move-detection \"first over\" event (the horse that first leaves cover to advance) | Deferred | v1.5 (S-1; `lead_uncovered_outside` is positional) |\n"
    "| Official per-runner tracking data as a source | To evaluate before the pilot | could supersede M2–M4 for rank/position (RP-6) |\n"
    "| Pose-based gait classification for breaks | Deferred | v1.5 (RP-16; needs tight-shot resolution) |\n"
    "| Track-landmark / phase-topology detection | Banned | reconstruct downstream from `piste` + distance + RK (DR-07) |")

# ---------------------------------------------------------------- §14 changelog (L-08) and Annex A (L-45)
rep("L-08", "| 1.2.0 | 2026-07-25 | Post-corpus-verification corrections",
    "| 2.0.0-draft | 2026-11-04 | DRAFT cut from 1.2.0 per RECON-2.0.0 and `RECON-2.0.0-patches.md` (edit ledger L-01…L-45; `tools/cut_draft.py`). Cover tier-independent with span-bounded tiers (D-26); headline re-cut to the uncovered-outside mask, `first_over` → `lead_uncovered_outside` (D-27); DETACHED diagnostic-only (D-28); cap/target split, ≥ 2× playback (D-29); `official_assumed` evidence bar (D-30); statistical honesty package (D-31); quantized canonical export (D-32); kill-gates + pilot exemption (D-33); per-start-type anchor offsets/tolerances (D-34); per-stratum yield, dual headline reporting (D-35); DRAFT-until-evidence (D-36). New: `piste`, `autostart_row`, EC-14, §11.4, S-3/S-5/S-6 fixes, DR-10 rule. Open: OD-1x, OD-3, OD-4, RP-11, signal gate. No artifact migration (none exist under 1.x). |\n"
    "| 1.2.0 | 2026-07-25 | Post-corpus-verification corrections")
rep("L-45", "*End of SPEC-1.2.0.*",
    "- **Why cover is geometric and the headline is a mask (D-26/D-27):** the energetic toll is being outside *and* uncovered, independent of which lane; a cover definition that inherits tier clustering flips at an arbitrary boundary, and a headline on the `PARKED` label excludes the three-wide uncovered case it exists to measure. Labels stay categorical for the lexicon; the money metric follows the physics.\n"
    "- **Why `official_assumed` needs observed crossings (D-30):** D-25's defence rests on the reconstruction being a free corroborator; with zero observed crossings it corroborates nothing and adoption becomes the \"guess dressed as metadata\" D-25 forbids.\n"
    "- **Why the field-size cap is a known bias (DR-11):** the ≤ 14 cap and cinematic big-race realizations exclude the deepest betting pools by construction; the exclusion is missing-not-at-random and accepted for v1, and `qc.realization` makes it quantifiable rather than invisible.\n"
    "- **Why lateral scale is suspect (RP-5):** SW is derived from SL under an implicit fixed-yaw assumption; an oblique wide pan compresses lateral distances relative to longitudinal ones, and bends add axis error. OD-1x step 4 measures it; the fix, if needed, is a scale aid, not a homography.\n\n"
    "*End of SPEC-2.0.0-draft.*")


def cut(text: str) -> str:
    for lid, old, new in EDITS:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{lid}: expected exactly one match, found {n}: {old[:90]!r}")
        text = text.replace(old, new)
    return text


def main(argv: list[str]) -> int:
    out = cut(SRC.read_text(encoding="utf-8"))
    if "--check" in argv:
        ok = DST.exists() and DST.read_text(encoding="utf-8") == out
        print("draft matches cut" if ok else "draft DIFFERS from cut — re-run tools/cut_draft.py")
        return 0 if ok else 1
    DST.write_text(out, encoding="utf-8")
    print(f"wrote {DST} ({len(EDITS)} edits applied over {len({e[0] for e in EDITS})} ledger rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
