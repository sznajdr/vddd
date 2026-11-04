# M4 — Pack-Space Geometry

**Spec:** §2.2, §3, EC-13; 2.0.0 ledger L-10, L-11; D-26. **Status:** tiering + cover implemented as reference functions and tested; projection stubbed (needs M3 tracklets and OD-1x step 4 on lateral scale, RP-5).

| | |
|---|---|
| Input | ID-assigned tracklets + wide-pan frames + per-shot calibration (`travel_direction_sign`, `rail_side`). |
| Output | Per frame per runner: `(l_sl, w_sw, rank_long, tier_cluster, tier, order_ambiguous, rail_ref_w_sw, rail_ref_conf, conf)`. |
| Acceptance | ≥ 300 dev golden frames: order agreement ≥ 0.97, tier agreement ≥ 0.92, rail-ref validity F1 ≥ 0.90. |
| DoD | Degenerate frames → `conf = 0`; near-ties → `order_ambiguous`; **cluster span ≤ `max_tier_span_sw` (unit test, 14 evenly spread runners)**. |

Gate: G-2 (M3 produces ID-assigned tracklets on ≥ 3 dev races within budget). The throwaway pilot is exempt (RP-2).
