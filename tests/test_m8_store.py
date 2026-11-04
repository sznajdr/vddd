from tripstate.m8_storage import Store, ordinal_ids


def seg_rows(race, state="POCKET", n=2):
    rows = [{"race_id": race, "saddle_no": 1, "state_kind": "base", "state": state, "covered": True,
             "lead_uncovered_outside": False, "lead_uncovered_outside_ambiguous": False, "tier_attr": None,
             "end_attr": None, "method": "cv_extract", "t_start_frac": i * 0.5, "t_end_frac": (i + 1) * 0.5,
             "confidence": 0.9, "visibility": "visible", "start_truncated": False, "end_truncated": False}
            for i in range(n)]
    return ordinal_ids(rows, "seg_id", "t_start_frac")


def qc_row(race, chartable, codes=()):
    return {"race_id": race, "chartable": chartable, "failure_codes": list(codes), "coverage_race": 0.8,
            "coverage_final_third": 0.9, "human_minutes": 4.0, "stratum": "night", "id_suspect": False,
            "anchor_suspect": False}


def race_row(race):
    return {"race_id": race, "date": "2026-11-03", "meeting": "R1", "race_no": 4, "base_distance_m": 2100,
            "start_type": "autostart", "start_format": "autostart", "start_handicap": False, "piste": "GP",
            "metadata_conflict_codes": []}


def test_schema_applies_and_round_trips():
    st = Store()
    assert "state_segments" in st.tables() and st.primary_key("state_segments")[:3] == ["race_id", "saddle_no", "seg_id"]
    st.insert("races", [race_row("r1")], producer_version="pv1", created_at="t1")
    st.insert("qc", [qc_row("r1", True)], producer_version="pv1", created_at="t1", extractor_version="ex1", threshold_set_version="TS-0")
    st.insert("state_segments", seg_rows("r1"), producer_version="pv1", created_at="t1", extractor_version="ex1", threshold_set_version="TS-0")
    rows = st.rows("state_segments")
    assert len(rows) == 2 and rows[0]["covered"] is True and rows[0]["schema_version"] == "2.0.0-draft"
    assert st.rows("qc")[0]["failure_codes"] == []


def test_default_reads_exclude_unchartable_and_override_is_diagnostic_only():
    st = Store()
    for r, ok in (("good", True), ("bad", False)):
        st.insert("races", [race_row(r)], producer_version="pv1", created_at="t")
        st.insert("qc", [qc_row(r, ok, () if ok else ("over_budget",))], producer_version="pv1", created_at="t", extractor_version="e", threshold_set_version="T")
        st.insert("state_segments", seg_rows(r), producer_version="pv1", created_at="t", extractor_version="e", threshold_set_version="T")
    assert {r["race_id"] for r in st.state_segments()} == {"good"}
    assert {r["race_id"] for r in st.state_segments(include_unchartable=True)} == {"good", "bad"}
    assert {r["race_id"] for r in st.feature_export()} == {"good"}
    try:
        st.feature_export(include_unchartable=True)
    except TypeError:
        pass
    else:
        raise AssertionError("feature_export must reject the override")
    # the SQL view mirrors the default path
    assert {r[0] for r in st.conn.execute("SELECT race_id FROM v_state_segments_chartable")} == {"good"}


def test_canonical_export_identical_across_runs_and_versions_coexist():
    a, b = Store(), Store()
    for st, ts_ in ((a, "2026-11-04T10:00:00"), (b, "2026-11-04T11:00:00")):
        st.insert("races", [race_row("r1")], producer_version="pv1", created_at=ts_)
        st.insert("qc", [qc_row("r1", True)], producer_version="pv1", created_at=ts_, extractor_version="e1", threshold_set_version="T1")
        st.insert("state_segments", seg_rows("r1"), producer_version="pv1", created_at=ts_, extractor_version="e1", threshold_set_version="T1")
    assert a.canonical_all() == b.canonical_all()
    assert '"created_at"' not in a.canonical("state_segments")
    # a second extractor version on the same race coexists and is queryable separately
    a.insert("state_segments", seg_rows("r1", "LEADER"), producer_version="pv2", created_at="x", extractor_version="e2", threshold_set_version="T1")
    assert len(a.rows("state_segments")) == 4
    assert a.canonical_sha("state_segments", "pv1") == b.canonical_sha("state_segments", "pv1")
    assert a.canonical_sha("state_segments") != b.canonical_sha("state_segments")


def test_unknown_column_rejected_and_shot_gap_is_race_level():
    st = Store()
    st.insert("races", [race_row("r1")], producer_version="pv", created_at="t")
    try:
        st.insert("qc", [dict(qc_row("r1", True), bogus=1)], producer_version="pv", created_at="t")
    except ValueError:
        pass
    else:
        raise AssertionError
    st.insert("events", [{"race_id": "r1", "saddle_no": 0, "event_id": 0, "type": "SHOT_GAP", "t_start_frac": 0.1,
                          "t_end_frac": 0.2, "source_shot_types": ["head_on", "tight"], "method": "cv_extract",
                          "review_status": "accepted", "human_confirmed": False}], producer_version="pv", created_at="t")
    assert st.rows("events")[0]["source_shot_types"] == ["head_on", "tight"]
    import sqlite3
    try:
        st.insert("events", [{"race_id": "r1", "saddle_no": 3, "event_id": 1, "type": "SHOT_GAP", "t_start_frac": 0.1,
                              "t_end_frac": 0.2, "method": "cv_extract", "review_status": "accepted", "human_confirmed": False}],
                  producer_version="pv", created_at="t")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("SHOT_GAP with a saddle number must violate the CHECK")
