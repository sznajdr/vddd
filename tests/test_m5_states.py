from tripstate.m5_states import RunnerGeom, classify_frame


def g(s, l, w, tier, conf=0.9, detected=True):
    return RunnerGeom(s, detected, conf, l, w, tier)


def states(rs):
    return {r.saddle_no: r.state for r in rs}


def test_rail_line_states(ts):
    rs = classify_frame([g(1, 3.0, 0.0, 1), g(2, 2.0, 0.0, 1), g(3, 1.0, 0.0, 1), g(4, -1.5, 0.0, 1)], ts)
    assert states(rs) == {1: "LEADER", 2: "POCKET", 3: "RAIL_COVERED", 4: "RAIL_UNCOVERED"}
    assert all(r.lead_uncovered_outside is False for r in rs)


def test_outside_states_and_lead(ts):
    rs = classify_frame([g(1, 3.0, 0.0, 1), g(5, 2.5, 1.0, 2), g(6, 1.0, 1.0, 2), g(7, -2.0, 1.0, 2), g(8, 2.0, 2.0, 3)], ts)
    st = states(rs)
    assert st[5] == "PARKED" and st[6] == "OUTSIDE_COVERED" and st[7] == "PARKED" and st[8] == "WIDE"
    by = {r.saddle_no: r for r in rs}
    assert by[5].lead_uncovered_outside is True and by[7].lead_uncovered_outside is False
    assert by[8].tier_attr == 3 and by[8].covered is False


def test_lead_tie_is_null_and_ambiguous(ts):
    rs = classify_frame([g(1, 5.0, 0.0, 1), g(5, 2.0, 1.0, 2), g(6, 2.05, 1.0, 2), g(7, -3.0, 1.0, 2)], ts)
    by = {r.saddle_no: r for r in rs}
    assert by[5].lead_uncovered_outside is None and by[5].lead_uncovered_outside_ambiguous is True
    assert by[6].lead_uncovered_outside is None and by[6].lead_uncovered_outside_ambiguous is True
    assert by[7].lead_uncovered_outside is False
    assert sum(1 for r in rs if r.lead_uncovered_outside is True) <= 1


def test_precedence_not_visible_unknown(ts):
    rs = classify_frame([g(1, 0.0, 0.0, 1, detected=False), g(2, 0.0, 0.0, 1, conf=0.1), g(3, 0.0, 0.0, None)], ts)
    assert states(rs) == {1: "NOT_VISIBLE", 2: "UNKNOWN", 3: "UNKNOWN"}
    assert all(r.covered is None and r.lead_uncovered_outside is None for r in rs)


def test_low_conf_overlay(ts):
    rs = classify_frame([g(1, 0.0, 0.0, 1, conf=0.4)], ts)
    assert rs[0].state == "LEADER" and rs[0].low_conf is True


def test_d26_table_gap_is_flagged_not_guessed(ts):
    # Tier-1 front runner with an outside runner 1 SL ahead and only 0.5 SW out -> covered under D-26.
    rs = classify_frame([g(1, 1.0, 0.0, 1), g(2, 2.0, 0.5, 2)], ts)
    by = {r.saddle_no: r for r in rs}
    assert by[1].state == "UNKNOWN" and by[1].reason == "table_gap_tier1_lead_covered"


def test_exact_tie_is_unknown_not_tiebreak(ts):
    # Equal l_sl: the saddle-number tiebreak must not decide LEADER vs RAIL_UNCOVERED.
    rs = classify_frame([g(1, 0.0, 0.0, 1), g(2, 0.0, 0.0, 1)], ts)
    assert {r.state for r in rs} == {"UNKNOWN"} and all(r.reason == "order_ambiguous" for r in rs)
    # A tie that cannot change either state (two WIDE runners) stays classified.
    rs = classify_frame([g(1, 5.0, 0.0, 1), g(2, 0.0, 2.0, 3), g(3, 0.05, 2.0, 3)], ts)
    assert [r.state for r in rs] == ["LEADER", "WIDE", "WIDE"]
