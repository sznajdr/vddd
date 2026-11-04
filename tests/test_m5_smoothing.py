"""M5 DoD: state-machine transitions unit-tested against synthetic trajectories."""
from tripstate.m5_states import FrameGeom, apply_tier_hysteresis, chart_race, smooth_runs

FPS = 25.0


def times(n):
    return [i / FPS for i in range(n)]


def traj(n, l, w, tier=1, conf=0.9, detected=True):
    """l, w: constants or callables of frame index."""
    out = []
    for i in range(n):
        li = l(i) if callable(l) else l
        wi = w(i) if callable(w) else w
        ti = tier(i) if callable(tier) else tier
        d = detected(i) if callable(detected) else detected
        out.append(FrameGeom(i / FPS, d, conf, li if d else None, wi if d else None, ti if d else None))
    return out


def base(rows, s):
    return [(r["state"], round(r["t_start_frac"], 3), round(r["t_end_frac"], 3)) for r in rows if r["saddle_no"] == s and r["state_kind"] == "base"]


def test_tier_hysteresis_retroactive_commit():
    t = times(50)
    raw = [1] * 10 + [2] * 5 + [1] * 10 + [2] * 20 + [1] * 5   # 0.2 s blip, then 0.8 s real change
    out = apply_tier_hysteresis(raw, t, 0.6)
    assert out[:25] == [1] * 25                      # blip suppressed
    assert out[25:45] == [2] * 20                    # committed from the run start
    assert out[45:] == [2] * 5                       # 0.2 s return is shorter than hysteresis: keeps tier 2


def test_smooth_runs_merges_short_blip_by_confidence():
    t = times(60)
    vals = ["POCKET"] * 25 + ["LEADER"] * 10 + ["POCKET"] * 25   # 0.4 s blip
    confs = [0.9] * 60
    src = smooth_runs(vals, t, confs, 1.0, lambda v: True, 1 / FPS)
    assert all(vals[src[i]] == "POCKET" for i in range(60))


def test_smooth_runs_never_merges_not_visible():
    t = times(60)
    vals = ["POCKET"] * 25 + ["NOT_VISIBLE"] * 10 + ["POCKET"] * 25
    src = smooth_runs(vals, t, [0.9] * 60, 1.0, lambda v: v != "NOT_VISIBLE", 1 / FPS)
    assert [vals[src[i]] for i in range(25, 35)] == ["NOT_VISIBLE"] * 10


def test_crossing_swaps_leader_and_pocket(ts):
    n = 100  # 4 s; B passes A at 2 s along the rail
    A = traj(n, lambda i: 0.0, 0.0)
    B = traj(n, lambda i: -1.0 + 2.0 * (i / n), 0.0)   # from 1 SL behind to 1 SL ahead
    rows = chart_race({1: A, 2: B}, times(n), [(0.0, 4.0)], 0.0, 4.0, ts)
    a, b = base(rows, 1), base(rows, 2)
    # Around the crossing |l_A - l_B| < rank_tie_sl, so both are UNKNOWN (order_ambiguous) for ~0.4 s;
    # the short RAIL_UNCOVERED runs either side merge into the adjacent covered state (min_state_s).
    assert [s for s, *_ in a] == ["LEADER", "UNKNOWN", "POCKET"]
    assert [s for s, *_ in b] == ["POCKET", "UNKNOWN", "LEADER"]
    assert a[1][1:] == b[1][1:]  # the ambiguous window is co-timed


def test_pocket_to_rail_uncovered_when_gap_opens(ts):
    n = 100
    A = traj(n, 0.0, 0.0)
    B = traj(n, lambda i: -1.0 if i < 50 else -3.0, 0.0)  # gap jumps beyond cover_max_sl at 2 s
    rows = chart_race({1: A, 2: B}, times(n), [(0.0, 4.0)], 0.0, 4.0, ts)
    assert [s for s, *_ in base(rows, 2)] == ["POCKET", "RAIL_UNCOVERED"]


def test_detached_front_and_rear_overlays(ts):
    n = 50
    A = traj(n, 10.0, 0.0)      # 10 SL clear in front
    B = traj(n, 0.0, 0.0)
    C = traj(n, -0.5, 1.0, tier=2)
    D = traj(n, -8.0, 0.0)      # 7.5 SL behind C
    rows = chart_race({1: A, 2: B, 3: C, 4: D}, times(n), [(0.0, 2.0)], 0.0, 2.0, ts)
    ov = {(r["saddle_no"], r["end_attr"]) for r in rows if r["state"] == "DETACHED"}
    assert ov == {(1, "front"), (4, "rear")}


def test_short_occlusion_is_kept_not_merged(ts):
    n = 100
    A = traj(n, 0.0, 0.0)
    B = traj(n, -1.0, 0.0, detected=lambda i: not (40 <= i < 50))  # 0.4 s NOT_VISIBLE
    rows = chart_race({1: A, 2: B}, times(n), [(0.0, 4.0)], 0.0, 4.0, ts)
    b = base(rows, 2)
    assert [s for s, *_ in b] == ["POCKET", "NOT_VISIBLE", "POCKET"]
    assert b[1] == ("NOT_VISIBLE", 0.4, 0.5)
    assert all(r["lead_uncovered_outside"] is None for r in rows if r["state"] == "NOT_VISIBLE")


def test_tier_drift_does_not_create_parked_blip(ts):
    n = 100
    A = traj(n, 0.0, 0.0)
    B = traj(n, -1.0, lambda i: 1.0 if 40 <= i < 48 else 0.0, tier=lambda i: 2 if 40 <= i < 48 else 1)  # 0.32 s flicker
    rows = chart_race({1: A, 2: B}, times(n), [(0.0, 4.0)], 0.0, 4.0, ts)
    assert [s for s, *_ in base(rows, 2)] == ["POCKET"]


def test_lead_uncovered_outside_changes_hands(ts):
    n = 100
    A = traj(n, 2.0, 0.0)                                   # leader, 2 SL clear ahead laterally far from B/C
    B = traj(n, lambda i: -1.0 if i < 50 else -4.0, 1.5, tier=2)   # parked, drops back at 2 s
    C = traj(n, -2.5, 1.5, tier=2)                           # parked, 1.5 SL behind B initially
    rows = chart_race({1: A, 2: B, 3: C}, times(n), [(0.0, 4.0)], 0.0, 4.0, ts)
    b = [r for r in rows if r["saddle_no"] == 2 and r["state_kind"] == "base"]
    c = [r for r in rows if r["saddle_no"] == 3 and r["state_kind"] == "base"]
    assert [r["lead_uncovered_outside"] for r in b] == [True, False]
    assert [r["lead_uncovered_outside"] for r in c] == [False, True]
    # at most one lead per co-timed frame
    assert b[0]["t_end_frac"] == c[0]["t_end_frac"]


def test_truncation_flags_at_cut_and_last_segment_ends_at_one(ts):
    n = 100
    A = traj(n, 0.0, 0.0)
    rows = chart_race({1: A}, times(n), [(0.0, 1.5), (2.5, 4.0)], 0.0, 4.0, ts)
    segs = [r for r in rows if r["saddle_no"] == 1]
    assert len(segs) == 2
    assert segs[0]["start_truncated"] is False and segs[0]["end_truncated"] is True
    assert segs[1]["start_truncated"] is True and segs[1]["end_truncated"] is False
    assert segs[1]["t_end_frac"] == 1.0
    assert all(r["t_start_frac"] < r["t_end_frac"] for r in segs)


def test_low_conf_overlay_inherits_and_splits(ts):
    n = 100
    A = traj(n, 0.0, 0.0, conf=0.45)                        # LOW_CONF throughout
    B = traj(n, lambda i: -1.0 if i < 50 else -3.0, 0.0)    # A's own state does not change, B's does
    rows = chart_race({1: A, 2: B}, times(n), [(0.0, 4.0)], 0.0, 4.0, ts)
    lc = [r for r in rows if r["saddle_no"] == 1 and r["state"] == "LOW_CONF"]
    assert len(lc) == 1 and lc[0]["covered"] is False and lc[0]["visibility"] == "visible"
