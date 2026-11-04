import numpy as np

from tripstate.m6_events import break_candidates


def synth(fps=25.0, dur=30.0, gallop=(10.0, 13.0), rank_drop=True, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(0, dur, 1 / fps)
    sl = 80.0
    amp = np.where((t >= gallop[0]) & (t < gallop[1]), 0.08, 0.02) if gallop else np.full(len(t), 0.02)
    freq = np.where((t >= gallop[0]) & (t < gallop[1]), 1.6, 2.2) if gallop else np.full(len(t), 2.2)
    h = sl * (0.6 + amp * np.sin(2 * np.pi * freq * t) + rng.normal(0, 0.004, len(t)))
    rank = np.full(len(t), 5.0)
    if gallop and rank_drop:
        rank[(t >= gallop[0] + 0.5) & (t < gallop[1])] = 8
        rank[t >= gallop[1]] = 8
    return t, rank.astype(int).tolist(), h.tolist(), sl


def test_detects_synthetic_break_near_true_start(ts):
    t, rank, h, sl = synth()
    c = break_candidates(t, rank, h, sl, ts)
    assert len(c) == 1, c
    assert abs(c[0].t_start_s - 10.0) <= ts["break_match_tolerance_s"]
    assert c[0].t_end_s is not None and 12.5 <= c[0].t_end_s <= 14.5
    assert c[0].review_status == "pending" and c[0].score > 1.0


def test_clean_trot_yields_no_candidate(ts):
    t, rank, h, sl = synth(gallop=None)
    assert break_candidates(t, rank, h, sl, ts) == []


def test_break_open_at_end_has_null_end(ts):
    t, rank, h, sl = synth(dur=15.0, gallop=(12.0, 15.0))
    c = break_candidates(t, rank, h, sl, ts)
    assert len(c) == 1 and c[0].t_end_s is None   # DR-10: unobservable end stays NULL


def test_oscillation_alone_without_rank_drop_still_opens(ts):
    t, rank, h, sl = synth(rank_drop=False)
    c = break_candidates(t, rank, h, sl, ts)
    assert len(c) == 1 and c[0].signals["osc_z_max"] > ts["osc_change_z"]
