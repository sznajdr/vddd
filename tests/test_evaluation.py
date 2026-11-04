import math

from tripstate.evaluation import (
    break_candidate_recall,
    edit_score,
    f1_at_k,
    headline_score,
    macro_iou,
    mask_iou,
    pass_probability,
    plan_audit,
    segment_iou,
    wilson_ci,
)
from tripstate.evaluation.metrics import is_covered, is_uncovered_outside, per_runner_state_iou


def seg(state, a, b, covered=None, tier_attr=None, kind="base"):
    return {"saddle_no": 1, "state_kind": kind, "state": state, "covered": covered, "tier_attr": tier_attr,
            "t_start_frac": a, "t_end_frac": b}


def test_segment_iou_respects_mask_and_abstention():
    pred = [(0.0, 0.5)]
    true = [(0.2, 0.6)]
    assert abs(segment_iou(pred, true, [(0.0, 1.0)]) - 0.5) < 1e-9
    assert abs(segment_iou(pred, true, [(0.0, 0.5)]) - 0.6) < 1e-9     # mask clips truth to [0.2, 0.5]
    assert segment_iou([], [], [(0.0, 1.0)]) is None                      # empty union omitted, not 1
    # predicted NOT_VISIBLE inside the mask counts as a miss: pred has no POCKET there
    p = [seg("NOT_VISIBLE", 0.0, 0.5), seg("POCKET", 0.5, 1.0, True)]
    t = [seg("POCKET", 0.0, 1.0, True)]
    assert abs(per_runner_state_iou(p, t, [(0.0, 1.0)], "POCKET") - 0.5) < 1e-9


def test_masks_and_headline():
    p = [seg("PARKED", 0.0, 0.5, False), seg("WIDE", 0.5, 0.8, False, 3), seg("WIDE", 0.8, 1.0, True, 3)]
    t = [seg("PARKED", 0.0, 0.6, False), seg("OUTSIDE_COVERED", 0.6, 1.0, True)]
    m = [(0.0, 1.0)]
    uo = mask_iou(p, t, m, is_uncovered_outside)   # pred [0,0.8) vs true [0,0.6) -> 0.6/0.8
    cov = mask_iou(p, t, m, is_covered)            # pred [0.8,1) vs true [0.6,1) -> 0.2/0.4
    assert abs(uo - 0.75) < 1e-9 and abs(cov - 0.5) < 1e-9
    assert abs(headline_score(uo, cov, None) - (0.5 * 0.75 + 0.3 * 0.5)) < 1e-9
    assert headline_score(None, cov, 0.9) is None
    assert abs(macro_iou({"LEADER": None, "WIDE": 0.4, "RAIL_UNCOVERED": 0.8}) - 0.6) < 1e-9


def test_wilson_ci_8_of_10():
    p, lo, hi = wilson_ci(8, 10)
    assert p == 0.8 and 0.48 < lo < 0.50 and 0.94 < hi < 0.96   # ≈ [0.49, 0.94] as the review stated


def test_break_matching_one_to_one():
    m, n, pairs = break_candidate_recall([10.0, 10.5, 40.0], [10.2, 41.5, 90.0], 2.0)
    assert m == 2 and n == 3
    assert (0, 0) in pairs and (2, 1) in pairs           # candidate 1 cannot also claim truth 0


def test_edit_score_and_f1_penalize_flicker():
    t = [seg("POCKET", 0.0, 0.5, True), seg("LEADER", 0.5, 1.0, False)]
    good = [seg("POCKET", 0.0, 0.48, True), seg("LEADER", 0.48, 1.0, False)]
    flicker = [seg("POCKET", 0.0, 0.2, True), seg("LEADER", 0.2, 0.22, False), seg("POCKET", 0.22, 0.5, True), seg("LEADER", 0.5, 1.0, False)]
    assert edit_score(good, t) == 100.0 and edit_score(flicker, t) == 50.0
    assert f1_at_k(good, t, 0.5) == 1.0 and f1_at_k(flicker, t, 0.5) < 1.0
    # IoU barely notices the flicker:
    assert per_runner_state_iou(flicker, t, [(0.0, 1.0)], "POCKET") > 0.9


def test_audit_plan_deterministic_and_stratified():
    def vis(t):
        return [1, 2, 3, 4, 5]

    def trk(s, t):
        return (s, int(t // 10))  # tracklet changes every 10 s
    a = plan_audit("r1", "ex1", 0.0, 160.0, vis, trk)
    b = plan_audit("r1", "ex1", 0.0, 160.0, vis, trk)
    assert a.points == b.points and len(a.points) == 36
    ts_ = sorted({t for t, _ in a.points})
    assert len(ts_) == 12 and all(sum(1 for t in ts_ if k * 40 <= t < (k + 1) * 40) == 3 for k in range(4))
    assert a.effective_n >= 8 and not a.warnings
    c = plan_audit("r1", "ex1", 0.0, 160.0, vis, lambda s, t: s)   # one tracklet per runner all race
    assert c.effective_n == 5 and any("effective n" in w for w in c.warnings)
    assert plan_audit("r2", "ex1", 0.0, 160.0, vis, trk).points != a.points


def test_operating_characteristic_rp4():
    assert abs(pass_probability(0.99) - 0.947) < 0.005
    assert abs(pass_probability(0.98) - 0.835) < 0.005
    assert abs(pass_probability(0.95) - 0.459) < 0.005
    assert math.isclose(pass_probability(1.0), 1.0)
