# M4 — Pack-Space Geometry

**Spec:** §2.2, §3, EC-13; 2.0.0 ledger L-10, L-11; D-26. **Status:** tiering, cover and principal-axis projection (`ShotProjector`: motion axis with PCA fallback, calibration-driven orientation, SL/SW normalisation, ranks, ties, clusters, rail attachment) implemented and tested on synthetic renders; pixel-space rail detection is supplied by the caller. Lateral scale remains evidence-gated (RP-5). Options from the simulator study (research 11): `axis_source = rail`, `lateral_scale_mode = rail_fence_projective` with rail/fence polylines and the RP-23 foot-point correction; defaults stay as the spec states until the owner adopts them.

| | |
|---|---|
| Input | ID-assigned tracklets + wide-pan frames + per-shot calibration (`travel_direction_sign`, `rail_side`). |
| Output | Per frame per runner: `(l_sl, w_sw, rank_long, tier_cluster, tier, order_ambiguous, rail_ref_w_sw, rail_ref_conf, conf)`. |
| Acceptance | ≥ 300 dev golden frames: order agreement ≥ 0.97, tier agreement ≥ 0.92, rail-ref validity F1 ≥ 0.90. |
| DoD | Degenerate frames → `conf = 0`; near-ties → `order_ambiguous`; **cluster span ≤ `max_tier_span_sw` (unit test, 14 evenly spread runners)**. |

Gate: G-2 (M3 produces ID-assigned tracklets on ≥ 3 dev races within budget). The throwaway pilot is exempt (RP-2).

`frames_to_json` / `frames_from_json` (C8): the explicit per-race frame record (`tripstate.m4.frames/1`, every `RunnerGeometry` field per frame plus box heights) that `tools/export_calibration_inputs.py` turns into calibration sidecars.
