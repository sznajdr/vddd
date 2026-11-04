"""World-space synthetic race: scripted pack-space truth -> track metres -> pinhole camera -> image boxes.

Vehicle ASSUMPTIONS: horse + sulky length 4.3 m (SL_world), lane spacing 1.5 m (SW_world, = 0.35·SL,
i.e. the spec's sw_ratio), vehicle width 1.5 m, height 1.7 m. Lane k is centred at (k + 0.5)·SW_world
from the rail (rail_lane_center_offset_sw = 0.5). The camera sits in the grandstand south of the home
straight, elevated, pans at the pack centroid with a lag and zooms so SL projects to ~target_sl_px.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from tripstate.m4_geometry.projection import Box
from tripstate.synth.camera import PinholeCamera
from tripstate.synth.race import RunnerScript
from tripstate.synth.track import StadiumTrack

SL_WORLD_M = 4.3
SW_RATIO = 0.35
SW_WORLD_M = SL_WORLD_M * SW_RATIO
VEHICLE_W_M = 1.5
VEHICLE_H_M = 1.7


@dataclass
class WorldCamera:
    height_m: float = 18.0        # ASSUMED broadcast position height
    setback_m: float = 15.0       # ASSUMED distance behind the outer fence
    along_m: float = 0.0          # position along the home straight (0 = middle)
    lag_s: float = 0.12           # pan lag behind the pack centroid
    pan_wobble_m: float = 2.0     # operator correction oscillation of the aim point along the track
    pan_wobble_period_s: float = 3.0
    target_sl_px: float = 80.0
    image_size: tuple[int, int] = (1920, 1080)


@dataclass
class WorldRace:
    runners: list[RunnerScript]
    duration_s: float
    fps: float
    track: StadiumTrack = field(default_factory=StadiumTrack)
    camera: WorldCamera = field(default_factory=WorldCamera)
    s_start_m: float | None = None   # pack centre arc length at t = 0; None = in front of the stands (mid home straight)
    speed_m_s: float = 14.0       # ≈ 71 s/km
    t0: float = 0.0

    @property
    def tend(self) -> float:
        return self.t0 + self.duration_s

    def frames(self) -> list[float]:
        return [self.t0 + i / self.fps for i in range(round(self.duration_s * self.fps))]

    def __post_init__(self) -> None:
        if self.s_start_m is None:
            self.s_start_m = self.track.straight_m / 2.0

    def s_pack(self, t: float) -> float:
        return self.s_start_m + self.speed_m_s * (t - self.t0)

    def viewing_angle_deg(self, s: float) -> float:
        """Angle between the ground-projected camera line of sight and the track tangent at s (0 = along, 90 = side-on)."""
        import math
        p = self.track.point(s, 1.5 * SW_WORLD_M)
        c = self.camera_position()[:2]
        los = p - c
        los = los / np.linalg.norm(los)
        t = self.track.tangent(s)
        return math.degrees(math.acos(min(1.0, abs(float(np.dot(los, t))))))

    def runner_world(self, r: RunnerScript, t: float) -> tuple[float, float] | None:
        f = (t - self.t0) / self.duration_s
        if not r.is_visible(f):
            return None
        return self.s_pack(t) + r.l(f) * SL_WORLD_M, (r.w(f) + 0.5) * SW_WORLD_M

    def camera_position(self) -> np.ndarray:
        tr = self.track
        return np.array([self.camera.along_m, -tr.radius_m - tr.width_m - self.camera.setback_m, self.camera.height_m])

    def make_camera(self, t: float) -> PinholeCamera:
        cam = PinholeCamera(self.camera_position(), self.camera.image_size)
        s_aim = self.s_pack(max(self.t0, t - self.camera.lag_s))
        if self.camera.pan_wobble_m:
            s_aim += self.camera.pan_wobble_m * np.sin(2 * np.pi * (t - self.t0) / self.camera.pan_wobble_period_s)
        aim = self.track.point(s_aim, 1.5 * SW_WORLD_M)
        cam.look_at(np.array([aim[0], aim[1], 0.8]))
        cam.zoom_to(np.array([aim[0], aim[1], 0.8]), SL_WORLD_M, self.camera.target_sl_px)
        return cam

    def box_corners(self, s: float, d: float) -> np.ndarray:
        p = self.track.point(s, d)
        t = self.track.tangent(s)
        n = self.track.outward_normal(s)
        corners = []
        for a in (-SL_WORLD_M / 2, SL_WORLD_M / 2):
            for b in (-VEHICLE_W_M / 2, VEHICLE_W_M / 2):
                g = p + t * a + n * b
                corners.append([g[0], g[1], 0.0])
                corners.append([g[0], g[1], VEHICLE_H_M])
        return np.array(corners)

    def render_frame(self, t: float) -> dict:
        cam = self.make_camera(t)
        w, h = self.camera.image_size
        boxes: list[Box] = []
        world: dict[int, tuple[float, float]] = {}
        for r in self.runners:
            sd = self.runner_world(r, t)
            if sd is None:
                continue
            s, d = sd
            world[r.saddle_no] = (s, d)
            uv = cam.project(self.box_corners(s, d))
            if (uv[:, 2] <= 0).any():
                continue
            x1, y1, x2, y2 = uv[:, 0].min(), uv[:, 1].min(), uv[:, 0].max(), uv[:, 1].max()
            if x2 < 0 or y2 < 0 or x1 > w or y1 > h:
                continue
            boxes.append(Box(r.saddle_no, float(x1), float(y1), float(x2), float(y2), 0.95))
        sp = self.s_pack(t)
        rail = cam.project(np.array([[*self.track.rail_point(sp), 0.0]]))[0]
        fence = cam.project(np.array([[*self.track.fence_point(sp), 0.0]]))[0]
        rail_ahead = cam.project(np.array([[*self.track.rail_point(sp + 10.0), 0.0]]))[0]
        fence_ahead = cam.project(np.array([[*self.track.fence_point(sp + 10.0), 0.0]]))[0]
        ss = np.arange(sp - 60.0, sp + 60.0 + 1e-9, 3.0)
        rail_poly = cam.project(np.array([[*self.track.rail_point(x), 0.0] for x in ss]))
        fence_poly = cam.project(np.array([[*self.track.fence_point(x), 0.0] for x in ss]))
        rail_poly = rail_poly[rail_poly[:, 2] > 0][:, :2]
        fence_poly = fence_poly[fence_poly[:, 2] > 0][:, :2]
        return {"t": t, "boxes": boxes, "world": world, "s_pack": sp, "camera": cam,
                "rail_polyline_px": rail_poly, "fence_polyline_px": fence_poly,
                "rail_px": (float(rail[0]), float(rail[1])), "fence_px": (float(fence[0]), float(fence[1])),
                "rail_dir_px": (float(rail_ahead[0] - rail[0]), float(rail_ahead[1] - rail[1])),
                "fence_dir_px": (float(fence_ahead[0] - fence[0]), float(fence_ahead[1] - fence[1])),
                "location": self.track.describe(sp)}

    def render(self) -> list[dict]:
        return [self.render_frame(t) for t in self.frames()]

    def truth_tier(self, r: RunnerScript, t: float) -> int | None:
        f = (t - self.t0) / self.duration_s
        return None if not r.is_visible(f) else round(r.w(f)) + 1


def lateral_compression(race: WorldRace, s: float, lane_a: int = 0, lane_b: int = 1) -> dict:
    """OD-1x step 4 in simulation: apparent lane gap between two adjacent lanes at arc length s, in
    units of the apparent SL (median box long side), plus the ideal longitudinal and lateral px/m."""
    cam = race.make_camera(race.t0)  # any camera; re-aim at s
    aim = race.track.point(s, 1.5 * SW_WORLD_M)
    cam.look_at(np.array([aim[0], aim[1], 0.8]))
    cam.zoom_to(np.array([aim[0], aim[1], 0.8]), SL_WORLD_M, race.camera.target_sl_px)
    def box_of(lane: int):
        uv = cam.project(race.box_corners(s, (lane + 0.5) * SW_WORLD_M))
        return uv[:, 0].min(), uv[:, 1].min(), uv[:, 0].max(), uv[:, 1].max()
    ba, bb = box_of(lane_a), box_of(lane_b)
    sl_px = float(np.median([max(b[2] - b[0], b[3] - b[1]) for b in (ba, bb)]))
    ca = ((ba[0] + ba[2]) / 2, ba[3]); cb = ((bb[0] + bb[2]) / 2, bb[3])
    tan = race.track.tangent(s); nrm = race.track.outward_normal(s)
    t3 = np.array([tan[0], tan[1], 0.0]); n3 = np.array([nrm[0], nrm[1], 0.0])
    p = race.track.point(s, 1.0 * SW_WORLD_M)
    p3 = np.array([p[0], p[1], 0.0])
    long_px_m = cam.ground_scale_px_per_m(p3, t3)
    lat_px_m = cam.ground_scale_px_per_m(p3, n3)
    # lateral gap measured perpendicular to the projected track direction (what OD-1x step 4 measures)
    a2, b2 = cam.project(np.stack([p3, p3 + t3]))
    u_long = np.array([b2[0] - a2[0], b2[1] - a2[1]]); u_long /= np.linalg.norm(u_long)
    u_lat = np.array([u_long[1], -u_long[0]])
    gap_px = abs(float(np.dot(np.array(cb) - np.array(ca), u_lat)))
    return {"s": s, "location": race.track.describe(s), "sl_px": sl_px, "lane_gap_px": gap_px,
            "lane_gap_in_sl": gap_px / sl_px, "lane_gap_in_sw": gap_px / sl_px / SW_RATIO,
            "long_px_per_m": long_px_m, "lat_px_per_m": lat_px_m, "lat_over_long": lat_px_m / long_px_m,
            "fence_rail_px": float(np.linalg.norm(cam.project(np.array([[*race.track.fence_point(s), 0.0]]))[0][:2]
                                                  - cam.project(np.array([[*race.track.rail_point(s), 0.0]]))[0][:2]))}
