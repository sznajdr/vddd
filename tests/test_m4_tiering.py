from tripstate.m4_geometry import absolute_tiers, cluster_tiers, covered, split_by_span


def test_14_runners_evenly_spread_bounded(ts):
    # S-4 / L-10 unit test: 14 runners evenly spread at 0.1 SW spacing.
    w = [i * 0.1 for i in range(14)]
    saddles = list(range(1, 15))
    c = cluster_tiers(w, saddles, ts)
    # contiguous rail-outward, 1-based, spans bounded
    ids = [c[s] for s in saddles]
    assert ids == sorted(ids) and ids[0] == 1
    for cid in set(ids):
        vals = [w[i] for i in range(14) if ids[i] == cid]
        assert max(vals) - min(vals) <= ts["max_tier_span_sw"] + 1e-12
    assert len(set(ids)) >= 2  # 1.3 SW spread cannot be one tier


def test_median_linkage_does_not_chain(ts):
    # 0 / 0.3 / 0.6 / 0.9 must not collapse into one cluster (review S-4 note).
    c = cluster_tiers([0.0, 0.3, 0.6, 0.9], [1, 2, 3, 4], ts)
    assert c[1] == c[2] == c[3] == 1 and c[4] == 2


def test_two_clear_lanes(ts):
    c = cluster_tiers([0.05, 0.0, 1.05, 1.0, 2.1], [3, 1, 7, 5, 9], ts)
    assert c[1] == c[3] == 1 and c[5] == c[7] == 2 and c[9] == 3


def test_split_by_span_largest_gap():
    assert split_by_span([0.0, 0.2, 0.4, 0.9, 1.1, 1.3], 1.2) == [[0.0, 0.2, 0.4], [0.9, 1.1, 1.3]]
    assert split_by_span([0.0, 0.5, 1.0], 1.2) == [[0.0, 0.5, 1.0]]
    # ties -> lower-index gap
    assert split_by_span([0.0, 0.7, 1.4], 1.2) == [[0.0], [0.7, 1.4]]


def test_deterministic_saddle_tiebreak(ts):
    a = cluster_tiers([0.5, 0.5, 0.5], [9, 2, 5], ts)
    b = cluster_tiers([0.5, 0.5, 0.5], [2, 5, 9], ts)
    assert a == b == {2: 1, 5: 1, 9: 1}


def test_absolute_tiers_ec13(ts):
    clusters = {1: 1, 2: 2}
    w = {1: 0.5, 2: 1.6}
    assert absolute_tiers(clusters, w, 0.0, 0.9, ts) == clusters         # attached
    assert absolute_tiers(clusters, w, None, None, ts) == {1: None, 2: None}  # no rail ref
    assert absolute_tiers(clusters, w, 0.0, 0.1, ts) == {1: None, 2: None}   # low conf
    assert absolute_tiers({1: 1}, {1: 2.0}, 0.0, 0.9, ts) == {1: None}      # empty rail lane: never promote


def test_cover_predicate_d26(ts):
    l = {1: 1.0, 2: 0.0, 3: 0.0, 4: 3.0}
    w = {1: 0.0, 2: 0.0, 3: 1.0, 4: 0.0}
    assert covered(2, l, w, ts) is True          # 1 SL ahead, same lateral
    assert covered(3, l, w, ts) is False         # 1.0 SW off: >= cover_lat_sw 0.8
    assert covered(1, l, w, ts) is True          # 4 is exactly 2.0 SL ahead: closed interval -> covered
    assert covered(4, l, w, ts) is False         # nobody ahead


def test_cover_is_tier_independent(ts):
    # Off-the-wheel: 0.5 SW lateral, 0.8 SL behind -> covered under D-26 regardless of tier.
    l = {1: 0.8, 2: 0.0}
    w = {1: 0.0, 2: 0.5}
    assert covered(2, l, w, ts) is True
