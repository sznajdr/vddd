import numpy as np

from tripstate.m4_geometry import Box, ShotCalibration, ShotProjector, lateral_unit
from tripstate.synth import render_boxes, scripted_race


def test_lateral_unit_sign_convention():
    u = np.array([1.0, 0.0])                     # travelling right on screen
    assert np.allclose(lateral_unit(u, "right_of_travel"), [0.0, -1.0])   # rail below -> away = up (negative y)
    assert np.allclose(lateral_unit(u, "left_of_travel"), [0.0, 1.0])


def test_projection_recovers_lanes_order_and_axis(ts):
    race = scripted_race(duration_s=4.0)
    saddles = [r.saddle_no for r in race.runners]
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    frames = [proj.project(t, boxes, rail, 0.9, saddles) for t, boxes, rail in render_boxes(race)]
    f = frames[int(0.15 * len(frames))]  # f = 0.15 of the race: past the motion window, runner 5 still visible
    assert f.axis_method == "motion" and f.conf > 0.9
    ang = np.degrees(np.arctan2(f.axis[1], f.axis[0]))
    assert abs(ang - race.camera.direction_deg) < 1.0
    by = {r.saddle_no: r for r in f.runners}
    # truth at f = 0.15 of the 4 s race: ranks by l: 1 (0), 4 (-0.5), 2 (-1.0), 6 (-1.2), 3 (-2.2), 5 (-3.0), 7 (-4.0)
    assert [by[s].rank_long for s in (1, 4, 2, 6, 3, 5, 7)] == [1, 2, 3, 4, 5, 6, 7]
    assert by[1].tier == 1 and by[4].tier == 2 and by[6].tier == 3 and by[2].tier == 1
    assert abs((by[4].w_sw - by[1].w_sw) - 1.0) < 0.05 and abs((by[1].l_sl - by[2].l_sl) - 1.0) < 0.05
    assert by[2].order_ambiguous is False


def test_degenerate_frames_have_zero_conf(ts):
    proj = ShotProjector(ts, None, 25.0)   # no calibration
    f = proj.project(0.0, [Box(1, 0, 0, 80, 48), Box(2, 100, 0, 180, 48), Box(3, 200, 0, 280, 48)], None, None, [1, 2, 3])
    assert f.conf == 0.0 and all(r.conf == 0.0 and r.l_sl is None for r in f.runners)
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel"), 25.0)
    f = proj.project(0.0, [Box(1, 0, 0, 80, 48), Box(2, 100, 0, 180, 48)], None, None, [1, 2, 3])
    assert f.conf == 0.0 and any(not r.detected for r in f.runners)  # pack < 3 visible; missing runner flagged


def test_pca_fallback_before_motion_window(ts):
    race = scripted_race(duration_s=4.0)
    saddles = [r.saddle_no for r in race.runners]
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    t, boxes, rail = render_boxes(race)[0]
    f = proj.project(t, boxes, rail, 0.9, saddles)
    assert f.axis_method == "pca" and f.conf == ts["axis_pca_conf"]
    assert {r.saddle_no: r.rank_long for r in f.runners}[1] == 1


def test_no_rail_reference_means_unresolved_tiers(ts):
    race = scripted_race(duration_s=2.0)
    saddles = [r.saddle_no for r in race.runners]
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    f = None
    for t, boxes, _ in render_boxes(race):
        f = proj.project(t, boxes, None, None, saddles)
    assert all(r.tier is None and r.tier_cluster is not None for r in f.runners)   # EC-13: never promote


def test_axis_robust_to_box_jitter(ts):
    """RP-21: sub-pixel jitter on short displacements must not tilt the axis enough to break tiering."""
    import numpy as np

    from tripstate.m4_geometry import Box
    race = scripted_race(duration_s=6.0)
    saddles = [r.saddle_no for r in race.runners]
    rng = np.random.default_rng(0)
    proj = ShotProjector(ts, ShotCalibration(+1, "right_of_travel", True), race.fps)
    resolved = total = 0
    for t, boxes, rail in render_boxes(race):
        sx = 640 / 1920.0  # the pilot render scale: SL ≈ 27 px, 0.4 s displacement ≈ 4 px
        jb = [Box(b.saddle_no, *(np.array([b.x1, b.y1, b.x2, b.y2]) * sx + rng.normal(0, 0.3, 4)), b.conf) for b in boxes]
        f = proj.project(t, jb, (rail[0] * sx, rail[1] * sx), 0.9, saddles)
        if t > 1.0:
            total += 1
            resolved += int(all(r.tier is not None for r in f.runners if r.detected))
    assert resolved / total > 0.99, (resolved, total)
