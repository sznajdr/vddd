from tripstate.m7_qc import FAILURE_CODES, RaceQCInput, evaluate_gates, stratum_yield


def good():
    return RaceQCInput(0.8, 0.9, True, False, False, 0.05, 12, "attele", 4.5)


def test_clean_race_is_chartable(ts):
    r = evaluate_gates(good(), ts)
    assert r.chartable and r.failure_codes == []


def test_each_gate_trips_its_code(ts):
    import dataclasses as d
    cases = {
        "coverage_race_low": d.replace(good(), coverage_race=0.5),
        "coverage_final_third_low": d.replace(good(), coverage_final_third=0.6),
        "anchor_missing": d.replace(good(), anchors_present=False),
        "anchor_suspect": d.replace(good(), anchor_suspect=True),
        "id_suspect": d.replace(good(), id_suspect=True),
        "graphic_occlusion_high": d.replace(good(), pct_graphic_occluded=0.2),
        "field_too_large": d.replace(good(), field_size=15),
        "wrong_discipline": d.replace(good(), discipline="monte"),
        "over_budget": d.replace(good(), human_minutes=8.5),
    }
    for code, inp in cases.items():
        r = evaluate_gates(inp, ts)
        assert not r.chartable and code in r.failure_codes, code
        assert code in FAILURE_CODES


def test_cap_is_8_not_5(ts):
    import dataclasses as d
    assert evaluate_gates(d.replace(good(), human_minutes=7.9), ts).chartable  # D-29: cap != target


def test_stratum_yield_trigger(ts):
    rows = [(("day", "<=10", "autostart", "GP"), True)] * 8 + [(("day", "<=10", "autostart", "GP"), False)] * 2
    rows += [(("night", "11-14", "volte_handicap", "GP"), True)] * 2 + [(("night", "11-14", "volte_handicap", "GP"), False)] * 8
    y = stratum_yield(rows, ts)
    assert abs(y["overall"] - 0.5) < 1e-9
    assert y["review_trigger"] == [("night", "11-14", "volte_handicap", "GP")]
