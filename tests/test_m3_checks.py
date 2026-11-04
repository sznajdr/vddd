from tripstate.m3_track.checks import (
    FinishInputs,
    finish_check,
    reconstruct_crossings,
    start_check_autostart,
    start_check_volte,
)
from tripstate.pilot.detect import Detection


def test_relegation_fixture_keeps_first_past_and_resolves_inconclusive():
    """First past the post (7) later rétrogradé: t_end stays on 7, check inconclusive without id_suspect,
    basis final_revision_carveout, method observed_crossing (never official_assumed)."""
    inp = FinishInputs(observed_crossings=[(7, 100.0), (3, 100.4), (5, 100.9)], coverage_before_first_crossing=True,
                       official_order=[3, 5, 7, 2], arrival_revised=True, revision_implicated={7})
    r = finish_check(inp, finish_evidence_min_k=3)
    assert r.finish_check_basis == "final_revision_carveout" and r.finish_check_status == "inconclusive"
    assert not r.id_suspect and r.first_past_saddle_no == 7 and r.first_past_method == "observed_crossing"


def test_zero_crossing_fixture_never_official_assumed():
    """Head-on finish, nothing observed crossing, no revision evidence -> NULL, inconclusive (D-30)."""
    inp = FinishInputs(observed_crossings=[], coverage_before_first_crossing=False, official_order=[4, 1, 9], arrival_revised=None)
    r = finish_check(inp, finish_evidence_min_k=3)
    assert r.first_past_saddle_no is None and r.first_past_method is None and r.finish_evidence_n == 0
    assert any("D-30" in n for n in r.notes) and r.finish_check_status == "inconclusive"


def test_official_assumed_requires_k_consistent_crossings():
    base = {"coverage_before_first_crossing": False, "official_order": [4, 1, 9, 2], "arrival_revised": None}
    r = finish_check(FinishInputs(observed_crossings=[(1, 50.2), (9, 50.5), (2, 51.0)], **base), 3)
    assert r.finish_check_status == "pass" and r.first_past_saddle_no == 4 and r.first_past_method == "official_assumed" and r.finish_evidence_n == 3
    r2 = finish_check(FinishInputs(observed_crossings=[(1, 50.2), (9, 50.5)], **base), 3)
    assert r2.first_past_saddle_no is None and r2.finish_check_status == "pass"
    r3 = finish_check(FinishInputs(observed_crossings=[(1, 50.2), (9, 50.5), (2, 51.0)], **dict(base, arrival_revised=False)), 3)
    assert r3.first_past_method == "official_unrevised" and r3.finish_check_basis == "final_unrevised"


def test_contradiction_routes_to_adjudication_then_outcomes():
    inp = FinishInputs(observed_crossings=[(9, 50.0), (1, 50.3), (4, 50.6)], coverage_before_first_crossing=True,
                       official_order=[4, 1, 9], arrival_revised=None)
    r = finish_check(inp, 3)
    assert r.finish_check_status == "pending_adjudication" and r.needs_adjudication and r.first_past_saddle_no == 9
    r_id = finish_check(FinishInputs(**{**inp.__dict__, "adjudication": "identity_error", "adjudicated_first_past": 4}), 3)
    assert r_id.finish_check_status == "mismatch" and r_id.id_suspect
    r_rev = finish_check(FinishInputs(**{**inp.__dict__, "adjudication": "arrival_revision"}), 3)
    assert r_rev.finish_check_status == "inconclusive" and r_rev.arrival_revised is True and not r_rev.id_suspect
    r_auth = finish_check(FinishInputs(**{**inp.__dict__, "arrival_revised": False}), 3)
    assert r_auth.finish_check_status == "mismatch" and r_auth.id_suspect


def test_reconstruct_crossings_from_boxes():
    line = ((400.0, 0.0), (400.0, 300.0))   # vertical finish line at x = 400
    tl = {}
    for f in range(20):
        tl[f] = {1: Detection(300 + f * 10, 100, 340 + f * 10, 130, 1.0),    # crosses between frames 8 and 9 (foot x = 320+10f)
                 2: Detection(250 + f * 10, 100, 290 + f * 10, 130, 1.0)}    # crosses later
    out = reconstruct_crossings(tl, line, fps=10.0)
    assert [s for s, _ in out] == [1, 2]
    assert abs(out[0][1] - 0.8) < 1e-6 and abs(out[1][1] - 1.3) < 1e-6


def test_start_check_autostart_two_rows():
    posts = {s: s for s in range(1, 13)}
    rows = {s: (1 if s <= 9 else 2) for s in posts}
    lineup = {s: (0.0, (s - 1) * 1.0) for s in range(1, 10)}        # front row in post order laterally
    lineup.update({10: (-1.5, 1.0), 11: (-1.5, 3.0), 12: (-1.5, 5.0)})   # second row: presence only, any order
    assert start_check_autostart(lineup, posts, rows, 12).start_check_status == "pass"
    bad = dict(lineup); bad[3], bad[4] = lineup[4], lineup[3]
    assert start_check_autostart(bad, posts, rows, 12).start_check_status == "mismatch"
    assert start_check_autostart({1: (0, 0)}, posts, rows, 12).start_check_status == "inconclusive"


def test_start_check_volte_bands():
    rend = {1: 0, 2: 0, 3: 0, 4: 25, 5: 25, 6: 50}
    lineup = {1: (0.0, 0), 2: (-0.3, 1), 3: (0.2, 2), 4: (-6.0, 0), 5: (-6.4, 1), 6: (-12.1, 0)}
    assert start_check_volte(lineup, rend).start_check_status == "pass"
    swapped = dict(lineup); swapped[4], swapped[2] = lineup[2], lineup[4]
    assert start_check_volte(swapped, rend).start_check_status == "mismatch"
    smeared = {s: (-(rend[s] / 25) * 1.0, 0) for s in rend}     # bands only 1 SL apart
    assert start_check_volte(smeared, rend).start_check_status == "inconclusive"
