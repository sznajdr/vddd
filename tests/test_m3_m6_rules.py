from tripstate.m3_track.checks import anchor_check
from tripstate.m6_events.breaks import positions_lost


def test_anchor_check_per_start_type(ts):
    r = anchor_check(160.0, 158.5, "volte", ts)
    assert r["anchor_check_status"] == "pass" and abs(r["anchor_duration_delta_s"] - 1.5) < 1e-9
    r = anchor_check(163.0, 158.5, "autostart", ts)
    assert r["anchor_check_status"] == "mismatch" and r["anchor_suspect"]
    r = anchor_check(163.0, None, "autostart", ts)
    assert r["anchor_check_status"] == "inconclusive" and not r["anchor_suspect"]


def test_positions_lost_strict_f7():
    assert positions_lost(3, 7, frozenset({1, 2, 3, 4, 5, 6, 7}), frozenset({1, 2, 3, 4, 5, 6, 7})) == (4, 7)
    assert positions_lost(3, 2, frozenset({1, 2, 3, 4}), frozenset({1, 2, 3})) == (None, None)  # tail lost -> NULL
    assert positions_lost(None, 2, frozenset(), frozenset()) == (None, None)
