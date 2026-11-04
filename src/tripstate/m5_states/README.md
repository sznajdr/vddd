# M5 — State Machine

**Spec:** §2.3–2.4, §3.4; ledger L-12, L-13, L-25; D-27. **Status:** classification table (incl. §2.2 `order_ambiguous` → UNKNOWN, exact ties included), DETACHED overlay, tier hysteresis, min-duration smoothing of cover and states, lead recompute and segment emission implemented; synthetic-trajectory tests cover crossing, rail-uncovered gap, front/rear detachment, short occlusion, tier drift, lead changes, truncation at cuts and LOW_CONF inheritance (M5 DoD).

| | |
|---|---|
| Input | M4 per-frame geometry. |
| Output | Base-state segments + `DETACHED` / `LOW_CONF` overlays, smoothed, with `state_kind`, `covered`, `lead_uncovered_outside`, `lead_uncovered_outside_ambiguous`, `tier_attr`, `confidence`, `visibility`, truncation flags. |
| Acceptance | Dev hand charts: macro base-state IoU ≥ 0.80; **uncovered-outside mask IoU and covered-mask IoU ≥ 0.85** (RP-1 re-reference). |
| DoD | Exhaustive per-frame classification; unit tests on synthetic trajectories (crossing, rail-uncovered gaps, detachment, short occlusion, tier drift, lead changes). |

**RP-11 resolved (ledger L-46):** the front tier-1 runner remains `LEADER` when covered by an outside runner. `covered = true` is retained independently; no new base state or inferred identity is introduced. The covered-leader fixture and rail-rank tie fixture cover both precedence and abstention.
