from tripstate.m7_qc import realization_tag, runner_qc_row


def seg(state, a, b):
    return {"state_kind": "base", "state": state, "t_start_frac": a, "t_end_frac": b}


def test_fractions_and_occlusions():
    segs = [seg("POCKET", 0.0, 0.4), seg("NOT_VISIBLE", 0.4, 0.5), seg("UNKNOWN", 0.5, 0.6), seg("LEADER", 0.6, 1.0)]
    r = runner_qc_row("r", 1, segs)
    assert abs(r["pct_time_visible"] - 0.9) < 1e-9 and abs(r["pct_time_stateable"] - 0.8) < 1e-9
    assert abs(r["pct_final_third_visible"] - 1.0) < 1e-9 and abs(r["pct_final_third_stateable"] - 1.0) < 1e-9
    assert r["occl_events"] == 1 and r["terminal_before_final_third"] is False and r["denom_end_frac"] == 1.0


def test_shot_gaps_count_for_neither_numerator():
    segs = [seg("POCKET", 0.0, 0.5), seg("POCKET", 0.7, 1.0)]     # [0.5, 0.7) is a SHOT_GAP, no segments there
    r = runner_qc_row("r", 1, segs, shot_gaps=[(0.5, 0.7)])
    assert abs(r["pct_time_visible"] - 0.8) < 1e-9                 # denominator stays [0, 1]


def test_terminal_runner_ec03():
    segs = [seg("RAIL_COVERED", 0.0, 0.5)]
    r = runner_qc_row("r", 5, segs, terminal=("pulled_up", 0.5))
    assert r["denom_end_frac"] == 0.5 and abs(r["pct_time_visible"] - 1.0) < 1e-9
    assert r["pct_final_third_visible"] is None and r["pct_final_third_stateable"] is None and r["terminal_before_final_third"] is True
    r2 = runner_qc_row("r", 5, [seg("RAIL_COVERED", 0.0, 0.8)], terminal=("dai", 0.8))
    assert r2["terminal_before_final_third"] is False and abs(r2["pct_final_third_visible"] - 1.0) < 1e-9


def test_realization_tag():
    assert realization_tag(16) == "field_gt_14" and realization_tag(12, True) == "cinematic_big_race" and realization_tag(12) == "none"
