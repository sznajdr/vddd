# SPEC-2.0.0-draft — Vincennes Attelé Trip-State Extraction Pipeline

**Status:** DRAFT (D-36). Not normative for golden charting or calibration. Agents MAY build M0, schema migrations and tooling scaffolds against it.
**Version:** 2.0.0-draft
**Diff base:** `SPEC-1.2.0.md` (FROZEN, last of the 1.x line). This file is 1.2.0 **plus the delta ledger below**. Until the delta is applied section by section (task P1), the ledger is the authoritative statement of what 2.0.0 changes; where ledger and 1.2.0 text disagree, the ledger wins.
**Promotion rule (D-36):** this file becomes `SPEC-2.0.0.md` with Status FROZEN in one commit when (1) every `[EG: OD-1x]` marker in `registers/evidence_gated.yaml` is instantiated, (2) every kill-gate in `registers/kill_gates.yaml` evaluates `pass`, (3) D-26…D-36 are appended to §1, (4) `tools/freeze_check.py` exits 0.
**Why MAJOR:** D-17 reopened (headline metric re-cut), a D-08-frozen core definition changes (cover), a payload field is renamed (`first_over` → `lead_uncovered_outside`).

---

## Delta ledger (apply to the 1.2.0 text; one row = one edit task)

Legend: **now** = evidence-independent, lands verbatim. **EG** = structure lands now, value instantiated by OD-1x. **reg** = out-of-scope register entry.

### Header, §0, §14

| # | Section | Edit | Source | Gate |
|---|---|---|---|---|
| L-01 | Header | Version 2.0.0-draft; Status DRAFT; promotion rule above. | S-8, D-36 | now |
| L-02 | §0.2 DoD-1 | Floors re-referenced: **uncovered-outside mask IoU** (`tier ≥ 2 ∧ covered = false`) and covered-mask IoU, both ≥ 0.85. `IoU(PARKED)` is no longer a DoD floor. | F-2, D-27; patch RP-1 | now |
| L-03 | §0.2 DoD-2 | "pre-review candidate recall point estimate ≥ 0.80 with Wilson 95% CI **reported**; no certification claim at n = 10." | F-4, D-31 | now |
| L-04 | §0.2 DoD-3 | Median ≤ 5 min `[EG: OD-1x → pilot median rounded up]`; measured over ≥ 20 consecutive eligible attempts. Cap is Q-7, not DoD-3. | B-2, D-29 | EG |
| L-05 | §0.2 DoD-5 | "reproduces an identical **quantized canonical** payload (§9)". | F-6, D-32 | now |
| L-06 | §0.3 | OD-1 → **OD-1x** (`protocols/OD-1x/PROTOCOL.md`). OD-3, OD-4 unchanged. | B-1 | now |
| L-07 | New §0.4 Kill-gates | Content = `registers/kill_gates.yaml`. Plus the **pilot exemption**: the 5-race pilot runs on a throwaway stack exempt from G-1…G-3; its outputs are freeze evidence only. | S-7, D-33; patch RP-2 | EG values |
| L-08 | §14 changelog | Entry for 2.0.0-draft; entry template for 2.0.0 FROZEN. | — | now |

### §1 Decision log

| # | Edit | Gate |
|---|---|---|
| L-09 | Append D-26…D-36 from `decisions/DECISION-LOG.md` **at freeze only**. | freeze |

### §2 Definitions

| # | Section | Edit | Source | Gate |
|---|---|---|---|---|
| L-10 | §2.2 Lateral tier | After clustering: any cluster whose span (max − min `w_sw`) > `max_tier_span_sw` splits recursively at its largest internal gap (deterministic; ties → lower-index gap). Unit test: 14 runners evenly spread. | S-4, D-26 | now / EG sanity |
| L-11 | §2.2 Cover | **Replace**: `covered(X) ⇔ ∃ Y valid: (l_Y − l_X) ∈ [cover_min_sl, cover_max_sl] ∧ \|w_X − w_Y\| < cover_lat_sw`. Tier-independent. §3.4 min-duration smoothing applies to the predicate. | F-1, D-26 | now / EG value |
| L-11b | §3.1–3.3 | `[OPEN: RP-19/22/23]` optional lateral and axis modes from the simulator study: rail-line axis source, 1-D projective lateral coordinate from rail + fence + vanishing point with polyline datum and foot-point correction; carve-out language for §3.3. | RP-19…RP-25 | now (text), owner (adoption) |
| L-12 | §2.3 PARKED row | `first_over` → `lead_uncovered_outside`; `first_over_ambiguous` → `lead_uncovered_outside_ambiguous`. Positional sense documented: "the uniquely furthest-advanced `PARKED` runner at this frame" (tie under `rank_tie_sl` → NULL + ambiguous), **not** the move-detection event. **RP-11:** under D-26 a tier-1 front runner can be covered by an outside runner; 1.2.0's table has no row for it; reference implementation emits `UNKNOWN` with reason `table_gap_tier1_lead_covered` until the owner decides. | S-1, D-27; patch RP-3 | now |
| L-13 | §2.3 note | Labels unchanged; the headline metric no longer measures the PARKED label (see §6.2). Asymmetry label-vs-mask is intentional. | F-2 | now |
| L-14 | §2.4 DETACHED | Add cross-reference to D-28 (diagnostic-only in metrics). Detached **groups** → §12 register, v1.5. | F-3, D-28 | now / reg |
| L-15 | §2.5 BREAK | `positions_lost` valid only when the visible-runner set is identical at both samples, else NULL; add `positions_lost_basis_n`. | F-7, D-31 | now |
| L-16 | §2.5 BREAK | DR-10: a break open at `t_frac = 1.0` → `t_end_frac = NULL`, `recovered = NULL`; expected to coincide with DAI; agents MUST NOT "fix" it. | DR-10 | now |
| L-10b | §3.1 | Axis estimation hardened: length-weighted axial mean over displacements ≥ `axis_min_vector_sl`·SL, temporal smoothing `axis_smooth_s`; sensitivity statement `Δw ≈ (SL/SW)·l·sin δ` (≈ 1° accuracy needed on a 5 SL pack). Found by the synthetic pilot (RP-21). | RP-21 | now |
| L-17 | §2.6 | Normative sentence: `t_frac` is race-clock fraction, not per-runner course fraction; downstream conditions on `base_distance_m` / `distance_run_m` / `piste`. Landmark detection stays banned; approximate track position is reconstructible downstream from `piste` + distance + RK. | S-2, DR-07 | now |

### §4 Modules

| # | Section | Edit | Source | Gate |
|---|---|---|---|---|
| L-18 | M0 rule 4 | Branch 4 statuses: elapsed-only + plausible → `direct_elapsed`; km-rate-only + plausible → `km_rate_derived`. | S-3 | now |
| L-19 | M0 | `plausible_km_rate_min_s` 55 → **65**. | S-5 | now |
| L-20 | M0 input/output | `races.piste ∈ {GP, PP}` from ingest, never inferred from distance. `runners.autostart_row ∈ {1, 2, NULL}`. | DR-06, DR-04 | now |
| L-21 | M3 DoD (a) rung (ii) | `official_assumed` requires ≥ `finish_evidence_min_k` observed crossings (default 3 `[EG]`), all consistent with the reference order. Zero/insufficient → `first_past_saddle_no = NULL`, EC-12 `inconclusive`. New fixture: head-on finish, zero observed crossings → NULL, never `official_assumed`. | B-4, D-30 | now / EG value |
| L-22 | M3 DoD (b) | Autostart start check models two rows for fields > 9: front-row lateral order = post order; second row presence only, never order. | DR-04 | now |
| L-23 | M3 / EC-12 | Comparison uses `anchor_offset_{start_type}_s` and `anchor_tol_{start_type}_s` (see §7.1). | §1.3, D-34 | EG |
| L-24 | M3 tool DoD | Configurable ≥ 2× auto-play with auto-slowdown at flagged events. "Possible recall" flag surfaced (EC-14). | DR-12, DR-03 | now |
| L-25 | M5 Output/Acceptance | Rename in output payload; acceptance floors re-referenced to uncovered-outside mask IoU + covered-mask IoU (≥ 0.85, pre-calibration). | patch RP-1 | now |
| L-26 | M6 DoD | `dai_uncaught` splits into `dai_uncaught_break_expected` vs `dai_gait_other` (human tag at review). §7 MUST NOT tune break thresholds against `dai_gait_other`. | DR-09 | now |

### §5 Human workflow

| # | Edit | Source | Gate |
|---|---|---|---|
| L-27 | §5.1: tool plays at ≥ 2× with event slowdown; budget rule cap = Q-7 = **8 min** `[EG: ≈ p90 pilot]`. | DR-12, D-29 | EG |

### §6 Golden data & acceptance

| # | Section | Edit | Source | Gate |
|---|---|---|---|---|
| L-28 | §6.1 | Manifest authoritative for `split`; `hand_charts.split` is a denormalized copy validated at write time; mismatch → write rejected. Strata gain `piste`. | S-6, DR-06 | now |
| L-29 | §6.2 Headline | `0.5·IoU(uncovered_outside mask) + 0.3·IoU(covered mask) + 0.2·MacroIoU(rest)`, `rest = {LEADER, RAIL_UNCOVERED, WIDE}`. `DETACHED` reported descriptively per stratum, not in `rest`. | F-2, F-3, D-27, D-28 | now |
| L-30 | §6.2 empty-union rule | Scoped to DoD-1 components only. | F-3, D-28 | now |
| L-31 | §6.2 new metric | Per-stratum `chartable` rate: strata = day/night × field-size band × `start_format` × `piste`. Review trigger: any stratum yield < 0.5 × overall → manifest/threshold review before further charting. | B-3, D-35 | now / EG trigger |
| L-32 | §6.3 | Intent sentence: extractor accuracy ≠ operational yield; Q-7 exclusion deliberate; headline reported with and without Q-7 failures. DoD-2 CI reporting. | F-8, D-35 | now |
| L-33 | §6.4 | 12 timestamps stratified across 4 phase bins of `[t_0, t_end]` (3 per bin); runners resampled per timestamp; sampled points MUST touch ≥ 8 distinct tracklet intervals or the audit reports its effective n. Operating characteristic: accepts a 0.99-accuracy race w.p. ≈ 0.95; a 0.95-accuracy race passes ≈ **0.46** (patch RP-4). The audit is a smoke test, not a certificate. | F-5, D-31 | now |

### §7 Calibration

| # | Edit | Gate |
|---|---|---|
| L-34 | §7.1 new keys (all `[EG: OD-1x]`): `cover_lat_sw` 0.8, `max_tier_span_sw` 1.2, `anchor_offset_volte_s` 0.0, `anchor_offset_autostart_s` 0.0, `anchor_tol_volte_s` 2.0, `anchor_tol_autostart_s` 2.0, `finish_evidence_min_k` 3, `human_budget_cap_min` 8. Remove `anchor_duration_tolerance_s`. `plausible_km_rate_min_s` 55 → 65. Machine copy: `config/thresholds/TS-0.0.0-provisional.yaml`. | EG |

### §8 Edge cases

| # | Edit | Source | Gate |
|---|---|---|---|
| L-35 | EC-12 references offset + tol keys per start type. | D-34 | EG |
| L-36 | New **EC-14 faux départ / volte recall**: trigger = aborted start; heuristic = post-release deceleration / turn-back, restart footage; behaviour = `t_0` MUST anchor the **final** release, tool surfaces "possible recall"; QC field `recall_suspected`. | DR-03 | now |

### §9 Schema

| # | Edit | Source | Gate |
|---|---|---|---|
| L-37 | `state_segments` / `hand_charts`: `first_over` → `lead_uncovered_outside`, `first_over_ambiguous` → `lead_uncovered_outside_ambiguous`. | S-1; RP-3 | now |
| L-38 | `races.piste`; `runners.autostart_row`; `events.positions_lost_basis_n`; `qc.realization` coverage-failure tag; `qc.recall_suspected`. | DR-06, DR-04, F-7, DR-11, DR-03 | now |
| L-39 | Canonical payload: finite floats quantized to fixed decimals **before** hashing (SW/SL/conf: 4 dp; seconds: 3 dp; fractions: 6 dp); exact hex dropped. Determinism env knobs recorded under `producer_version`. Quantization applies to export only. | F-6, D-32 | now |
| L-40 | `versions.producer_kind` gains `pilot_throwaway`. | RP-2 | now |

### §10 QC gates

| # | Edit | Gate |
|---|---|---|
| L-41 | Q-7: `human_minutes ≤ human_budget_cap_min` (8 `[EG]`); `over_budget` non-waivable unchanged. | EG |

### §11 Lexicon

| # | Edit | Source | Gate |
|---|---|---|---|
| L-42 | §11.2 PARKED row: mapping to `lead_uncovered_outside` (positional sense) noted. | S-1 | now |
| L-43 | New §11.4 phase-vocab table (attested, `[C]` rules): « dès le départ » → early; « à mi-parcours » → mid; « dans le dernier tournant », « à l'entrée de la ligne droite », « dans la montée » → late; « sur le poteau » → late/stretch terminal. To be populated from the owner's corpus with provenance before activation. | DR-08 | now (shape) |

### §12 Register

| # | Edit | Gate |
|---|---|---|
| L-44 | Add: detached groups (v1.5); move-detection "first over" event (v1.5); fields > 14 already present — add DR-11 note; official LeTrot tracking data as alternative/augmenting source (evaluate before P4; see `RECON-2.0.0-patches.md` RP-6). | reg |

### Annex A

| # | Edit | Gate |
|---|---|---|
| L-45 | D-26/D-27 rationale (mask vs label). DR-11 selection-bias paragraph (≤ 14 cap + big-race realizations exclude deepest pools; MNAR by construction, accepted for v1). D-30 note tightening the D-25 defence. Lateral-scale caveat (RP-5): SW derived from SL assumes a fixed yaw; OD-1x step 4 measures it. | now |

---

## Changelog (2.0.0 line)

| Version | Date | Change |
|---|---|---|
| 2.0.0-draft | 2026-11-04 | Draft cut opened from 1.2.0 per RECON-2.0.0 §6 as a delta ledger (L-01…L-45) plus patches RP-1…RP-7. EG registry and kill-gates externalized to `registers/`. No artifact migration (none exist under 1.x). Open: OD-1x, OD-3, OD-4, signal gate. |
| 2.0.0 | _at freeze_ | _Template:_ EG registry instantiated from OD-1x sheets vN; kill-gates pass; D-26…D-36 appended; markers stripped; headline evaluation not yet run (first held-out evaluation appends its own entry). |

*End of SPEC-2.0.0-draft (ledger form).*
