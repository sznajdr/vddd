from tripstate.config import load_default


def test_loads_and_flags_eg(ts):
    assert ts.version == "TS-0.0.0-provisional"
    assert ts.calibrated is False
    assert ts["plausible_km_rate_min_s"] == 65  # S-5
    assert "cover_lat_sw" in ts.evidence_gated_keys()
    assert "anchor_duration_tolerance_s" not in ts.thresholds  # RP-10 retired


def test_missing_key_is_loud(ts):
    try:
        ts["no_such_key"]
    except KeyError as e:
        assert "§7.1" in str(e)
    else:
        raise AssertionError("expected KeyError")


def test_default_path_exists():
    assert load_default().spec_version == "2.0.0-draft"
