"""World-space simulator (A1): track geometry, camera projection, lateral compression (RP-5), bend error (RP-20),
rail/fence lateral scale (RP-19)."""
import math

import numpy as np

from tripstate.m4_geometry import ShotCalibration, ShotProjector
from tripstate.synth import StadiumTrack, WorldCamera, WorldRace, lateral_compression, scripted_race
from tripstate.synth.world import SW_WORLD_M


def test_track_closes_and_is_continuous():
    tr = StadiumTrack()
    assert abs(tr.straight_m * 2 + 2 * math.pi * tr.radius_m - tr.length_m) < 1e-9
    for s in np.linspace(0, tr.length_m, 400):
        a, b = tr.rail_point(s), tr.rail_point(s + 0.5)
        assert np.linalg.norm(b - a) < 0.5001
        t, n = tr.tangent(s), tr.outward_normal(s)
        assert abs(np.dot(t, n)) < 1e-9 and abs(np.linalg.norm(t) - 1) < 1e-9
    assert np.allclose(tr.rail_point(tr.length_m), tr.rail_point(0.0))
    assert tr.outward_normal(0.0)[1] < 0            # home straight: outward = south (towards the stands)
    assert tr.describe(tr.straight_m + 1) == "bend 1"


def test_camera_projects_sensibly():
    race = WorldRace(scripted_race(duration_s=4.0).runners, 4.0, 25.0)
    cam = race.make_camera(0.0)
    aim = race.track.point(race.s_pack(0.0), 1.5 * SW_WORLD_M)
    uv = cam.project(np.array([[aim[0], aim[1], 0.8]]))[0]
    assert abs(uv[0] - 960) < 1e-6 and abs(uv[1] - 540) < 1e-6 and uv[2] > 0   # aim point at the image centre
    near = race.track.point(race.s_pack(0.0), 2.5 * SW_WORLD_M)
    far = race.track.point(race.s_pack(0.0), 0.5 * SW_WORLD_M)
    vn = cam.project(np.array([[near[0], near[1], 0.0]]))[0][1]
    vf = cam.project(np.array([[far[0], far[1], 0.0]]))[0][1]
    assert vn > vf                                   # outer lane (near the stands) is lower in the image


def test_render_boxes_order_and_size():
    race = WorldRace(scripted_race(duration_s=4.0).runners, 4.0, 25.0)
    fr = race.render_frame(0.0)
    by = {b.saddle_no: b for b in fr["boxes"]}
    assert set(by) == {1, 2, 3, 4, 5, 6, 7}
    assert by[1].x1 > by[2].x1 > by[3].x1             # home straight travels +X = image right; leader furthest right
    sl = np.median([b.long_side for b in fr["boxes"]])
    assert 60 < sl < 100                              # auto-zoom keeps SL near target_sl_px
    assert by[4].y2 > by[1].y2                        # lane 1 (outer) lower than lane 0 (rail, far side)


def test_lateral_compression_side_on_is_severe():
    """RP-5 quantified: from an elevated side-on camera, lateral separation projects at ~h/depth of the
    longitudinal scale. The lane gap in SW units falls well below same_tier_sw."""
    race = WorldRace(scripted_race(duration_s=4.0).runners, 4.0, 25.0)
    tr = race.track
    m = lateral_compression(race, s=tr.straight_m / 2)              # middle of the home straight, in front of the stands
    assert 80 < race.viewing_angle_deg(tr.straight_m / 2) <= 90
    assert m["lat_over_long"] < 0.6
    assert m["lane_gap_in_sw"] < 0.6                  # adjacent lanes would merge under same_tier_sw = 0.6
    m_far = lateral_compression(race, s=tr.straight_m * 1.5 + math.pi * tr.radius_m)   # middle of the back straight
    assert m_far["lat_over_long"] < m["lat_over_long"]


def test_rail_fence_scale_recovers_lanes_where_sw_ratio_fails(ts):
    race = WorldRace(scripted_race(duration_s=3.0).runners, 3.0, 25.0, camera=WorldCamera(lag_s=0.25))
    saddles = [r.saddle_no for r in race.runners]
    frames = race.render()
    T = type(ts.thresholds["lateral_scale_mode"])

    def run(mode, axis="motion", poly=False):
        ts.thresholds["lateral_scale_mode"] = T("lateral_scale_mode", "geometry", mode)
        ts.thresholds["axis_source"] = T("axis_source", "geometry", axis)
        proj = ShotProjector(ts, ShotCalibration(+1, "left_of_travel", True), race.fps)
        ok = tot = 0
        for fr in frames:
            g = proj.project(fr["t"], fr["boxes"], fr["rail_px"], 0.9, saddles, fence_ref_px=fr["fence_px"],
                             rail_dir_px=fr["rail_dir_px"], fence_dir_px=fr["fence_dir_px"],
                             rail_polyline_px=fr["rail_polyline_px"] if poly else None,
                             fence_polyline_px=fr["fence_polyline_px"] if poly else None)
            if fr["t"] > 1.5:
                tot += 1
                tiers = {r.saddle_no: r.tier for r in g.runners if r.detected}
                truth = {r.saddle_no: race.truth_tier(r, fr["t"]) for r in race.runners}
                ok += int(all(tiers[s] == truth[s] for s in tiers if truth[s] is not None))   # detected runners only
        return ok / tot
    try:
        bad = run("sw_ratio")
        naive = run("rail_fence")
        motion_axis = run("rail_fence_projective", "motion")
        good = run("rail_fence_projective", "rail")
    finally:
        ts.thresholds["lateral_scale_mode"] = T("lateral_scale_mode", "geometry", "sw_ratio")
        ts.thresholds["axis_source"] = T("axis_source", "geometry", "motion")
    assert bad < 0.5 and naive < 0.5, (bad, naive)        # perspective defeats sw_ratio and the linear two-line scale
    assert good > 0.95 and good >= motion_axis, (motion_axis, good)  # rail-line axis is never worse than the pan/zoom-biased motion axis


def test_bend_error_single_datum_vs_polyline(ts):
    """RP-20: on a bend, one rail direction for the whole pack misplaces the tail laterally; the local rail
    datum (nearest polyline segment per runner) reduces the error."""
    tr = StadiumTrack()
    s_bend = tr.straight_m + math.pi * tr.radius_m / 2          # middle of bend 1
    race = WorldRace(scripted_race(duration_s=3.0).runners, 3.0, 25.0, s_start_m=s_bend - 14.0 * 1.5, camera=WorldCamera(lag_s=0.25))
    saddles = [r.saddle_no for r in race.runners]
    frames = race.render()
    T = type(ts.thresholds["lateral_scale_mode"])

    def mean_abs_w_err(poly):
        ts.thresholds["lateral_scale_mode"] = T("lateral_scale_mode", "geometry", "rail_fence_projective")
        ts.thresholds["axis_source"] = T("axis_source", "geometry", "rail")
        proj = ShotProjector(ts, ShotCalibration(+1, "left_of_travel", True), race.fps)
        errs = []
        for fr in frames:
            g = proj.project(fr["t"], fr["boxes"], fr["rail_px"], 0.9, saddles, fence_ref_px=fr["fence_px"],
                             rail_dir_px=fr["rail_dir_px"], fence_dir_px=fr["fence_dir_px"],
                             rail_polyline_px=fr["rail_polyline_px"] if poly else None,
                             fence_polyline_px=fr["fence_polyline_px"] if poly else None)
            if fr["t"] < 1.5 or g.conf == 0:
                continue
            w = {r.saddle_no: r.w_sw for r in g.runners if r.detected and r.w_sw is not None}
            truth_w = {s: (fr["world"][s][1] / SW_WORLD_M - 0.5) for s in w}
            # compare lateral differences relative to the leader (origin-free)
            for s, ws in w.items():
                errs.append(abs((ws - w[1]) - (truth_w[s] - truth_w[1])))
        return float(np.mean(errs))
    try:
        e_single = mean_abs_w_err(False)
        e_poly = mean_abs_w_err(True)
    finally:
        ts.thresholds["lateral_scale_mode"] = T("lateral_scale_mode", "geometry", "sw_ratio")
        ts.thresholds["axis_source"] = T("axis_source", "geometry", "motion")
    assert e_single > 0.15, e_single          # one direction for a 5 SL pack is measurably wrong on a 150 m bend
    assert e_poly < 0.5 * e_single, (e_single, e_poly)   # the local rail datum removes most of it
