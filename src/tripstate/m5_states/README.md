# M5 — State Machine

**Spec:** §2.3–2.4, §3.4; ledger L-12, L-13, L-25; D-27. **Status:** classification table implemented + tested; smoothing stubbed.

| | |
|---|---|
| Input | M4 per-frame geometry. |
| Output | Base-state segments + `DETACHED` / `LOW_CONF` overlays, smoothed, with `state_kind`, `covered`, `lead_uncovered_outside`, `lead_uncovered_outside_ambiguous`, `tier_attr`, `confidence`, `visibility`, truncation flags. |
| Acceptance | Dev hand charts: macro base-state IoU ≥ 0.80; **uncovered-outside mask IoU and covered-mask IoU ≥ 0.85** (RP-1 re-reference). |
| DoD | Exhaustive per-frame classification; unit tests on synthetic trajectories (crossing, rail-uncovered gaps, detachment, short occlusion, tier drift, lead changes). |

**Known table gap (RP-11):** with tier-independent cover (D-26), a tier-1 front runner can be covered by an outside runner slightly ahead within `cover_lat_sw`. 1.2.0's table has no row for it. The reference implementation emits `UNKNOWN` with reason `table_gap_tier1_lead_covered` until the owner decides (candidates: keep `LEADER` with `covered = true`, or new state). Logged in `spec/RECON-2.0.0-patches.md`.
