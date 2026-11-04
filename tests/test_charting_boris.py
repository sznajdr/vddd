from tripstate.charting import boris_to_hand_charts, parse_boris_export

HEADER = "Observation id\tSubject\tBehavior\tBehavioral category\tModifiers\tBehavior type\tStart (s)\tStop (s)\tDuration (s)\tComment start\n"


def row(subject, beh, kind, start, stop="", mods=""):
    return f"obs1\t{subject}\t{beh}\t\t{mods}\t{kind}\t{start}\t{stop}\t\t\n"


def export():
    return HEADER + "".join([
        row("camera", "T0", "POINT", 100.0), row("camera", "TEND", "POINT", 300.0),
        row("camera", "SHOT_GAP", "STATE", 200.0, 220.0, "head_on,tight"),
        row("1", "LEADER", "STATE", 100.0, 200.0), row("1", "LEADER", "STATE", 220.0, 300.0),
        row("2", "POCKET", "STATE", 100.0, 150.0), row("2", "PARKED", "STATE", 150.0, 200.0, "lead"),
        row("2", "WIDE", "STATE", 220.0, 300.0, "tier:3,uncovered"),
        row("2", "BREAK", "POINT", 160.0, "", "recovered"), row("2", "BREAKING", "STATE", 160.0, 170.0),
        row("3", "RAIL_COVERED", "STATE", 100.0, 180.0), row("3", "DETACHED", "STATE", 250.0, 300.0, "rear"),
        row("3", "NOT_VISIBLE", "STATE", 180.0, 200.0), row("3", "RAIL_UNCOVERED", "STATE", 220.0, 300.0),
    ])


def test_parse_and_convert_clean_chart():
    ev = parse_boris_export(export())
    res = boris_to_hand_charts(ev, "r1", "dev", charter_minutes=12.5)
    assert res["problems"] == [], res["problems"]
    assert res["anchors"] == {"t0_video_s": 100.0, "tend_video_s": 300.0}
    by = {(r["saddle_no"], r["state"], round(r["t_start_frac"], 3)): r for r in res["hand_charts"]}
    assert by[(1, "LEADER", 0.0)]["end_truncated"] is True and by[(1, "LEADER", 0.6)]["start_truncated"] is True
    assert by[(2, "PARKED", 0.25)]["lead_uncovered_outside"] is True
    assert by[(2, "WIDE", 0.6)]["tier_attr"] == 3 and by[(2, "WIDE", 0.6)]["covered"] is False
    assert by[(3, "DETACHED", 0.75)]["end_attr"] == "rear" and by[(3, "DETACHED", 0.75)]["state_kind"] == "overlay"
    assert by[(3, "NOT_VISIBLE", 0.4)]["covered"] is None and by[(3, "NOT_VISIBLE", 0.4)]["visibility"] == "not_visible"
    assert all(r["split"] == "dev" and r["charter_minutes"] == 12.5 and r["method"] == "human_chart" for r in res["hand_charts"])
    evs = {e["type"]: e for e in res["events"]}
    assert evs["SHOT_GAP"]["saddle_no"] == 0 and evs["SHOT_GAP"]["source_shot_types"] == ["head_on", "tight"]
    assert evs["BREAK"]["recovered"] is True and abs(evs["BREAK"]["t_end_frac"] - 0.35) < 1e-9 and evs["BREAK"]["review_status"] == "accepted"


def test_problems_are_reported():
    txt = HEADER + "".join([
        row("camera", "T0", "POINT", 100.0), row("camera", "TEND", "POINT", 300.0),
        row("1", "LEADER", "STATE", 100.0, 200.0), row("1", "POCKET", "STATE", 190.0, 300.0),   # overlap
        row("2", "WIDE", "STATE", 100.0, 300.0),                                                  # missing modifiers
        row("3", "LEADER", "STATE", 100.0, 150.0),                                                # uncharted gap w/o SHOT_GAP
    ])
    res = boris_to_hand_charts(parse_boris_export(txt), "r1", "heldout")
    joined = " | ".join(res["problems"])
    assert "overlapping" in joined and "WIDE" in joined and "uncharted" in joined


def test_missing_anchors():
    res = boris_to_hand_charts(parse_boris_export(HEADER + row("1", "LEADER", "STATE", 0, 10)), "r", "dev")
    assert res["hand_charts"] == [] and res["problems"]
