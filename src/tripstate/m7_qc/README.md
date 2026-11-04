# M7 — QC & Coverage

**Spec:** §10, §6.2–6.3; ledger L-29…L-32, L-41; D-11, D-28, D-35. **Status:** gate logic + per-stratum yield implemented and tested; `SHOT_GAP` emission and runner QC stubbed (need M1/M4 outputs).

| | |
|---|---|
| Input | All upstream outputs for a race. |
| Output | `qc` row (coverage fractions, human-minutes, stratum, `chartable`, failure codes, check statuses, `realization`, `recall_suspected`); `runner_qc` per non-NP runner; `SHOT_GAP` events. |
| Acceptance | Gate logic unit-tested; synthetic race violating each gate excluded; `SHOT_GAP` events complete and non-overlapping. |
| DoD | Default read APIs/exports exclude `unchartable`; `include_unchartable=true` is diagnostic-only and rejected by feature-export entry points. |

Closed failure codes: `anchor_missing, anchor_suspect, coverage_final_third_low, coverage_race_low, field_too_large, graphic_occlusion_high, id_suspect, over_budget, wrong_discipline`.
