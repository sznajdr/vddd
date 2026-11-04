from tripstate.m7_qc import Shot, coverage_fractions, shot_gap_events


def test_shot_gaps_maximal_and_boundaries():
    shots = [Shot("tight", 0, 100), Shot("wide_pan", 100, 150), Shot("head_on", 150, 160),
             Shot("replay_insert", 160, 170), Shot("wide_pan", 170, 190), Shot("graphic_fullscreen", 190, 220)]
    ev = shot_gap_events(shots, t0=100, tend=200)
    assert len(ev) == 2
    assert ev[0]["source_shot_types"] == ["head_on", "replay_insert"]
    assert ev[0]["shot_type_before"] == "wide_pan" and ev[0]["shot_type_after"] == "wide_pan"
    assert abs(ev[0]["t_start_frac"] - 0.5) < 1e-9 and abs(ev[0]["t_end_frac"] - 0.7) < 1e-9
    assert ev[1]["shot_type_after"] is None and ev[1]["t_end_frac"] == 1.0  # ends at the anchor


def test_gap_at_t0_has_null_before():
    ev = shot_gap_events([Shot("head_on", 0, 110), Shot("wide_pan", 110, 200)], 100, 200)
    assert ev[0]["shot_type_before"] is None and ev[0]["t_start_frac"] == 0.0


def test_no_gaps_when_all_wide():
    assert shot_gap_events([Shot("wide_pan", 0, 300)], 100, 200) == []


def test_coverage_fractions_durations():
    race, final = coverage_fractions([(100, 150), (170, 200)], 100, 200)
    assert abs(race - 0.8) < 1e-9
    # final third = [166.67, 200]: covered 170-200 = 30 of 33.33
    assert abs(final - 0.9) < 1e-9
