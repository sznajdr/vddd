"""Pack principal axis + projection — STUB (SPEC-2.0.0-draft §3.1–3.2).

Needs ID-assigned tracklets (M3). Contract: per frame, centroids = bbox center-bottom; motion
vectors over motion_window_s; robust mean axis (fallback PCA); canonicalize to +x; orient by
persisted travel_direction_sign; u_lat sign so increasing w = away from rail (rail_side per
shot, human-confirmed on low confidence). Outputs (l_sl, w_sw, rank_long, tier_cluster, tier,
order_ambiguous, rail_ref_w_sw, rail_ref_conf, conf). Degenerate frames -> conf = 0.
RP-5: lateral scale (sw_ratio) may need per-shot calibration; do not build until OD-1x step 4.
"""


def project_frame(*args, **kwargs):
    raise NotImplementedError("M4 projection: SPEC-2.0.0-draft §3.1–3.2; blocked on M3 + OD-1x step 4 (RP-5)")
