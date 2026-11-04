"""Stadium track model in metres (research 11; A1).

ASSUMPTIONS (documented, not measured): the track is a stadium (two straights + two semicircles) of
the published lap length; width and bend radius are placeholders until OD-1x / a track plan gives them.
Runners circulate counter-clockwise with the rail on the LEFT of travel (corde à gauche); the
grandstand is south of the home straight (negative Y), so on the home straight the rail is the FAR
side from the camera and the outer lanes are the near side.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

VINCENNES_GP_LENGTH_M = 1975.0   # published
VINCENNES_PP_LENGTH_M = 1325.0   # published (1 325–1 326 m)


@dataclass(frozen=True)
class StadiumTrack:
    length_m: float = VINCENNES_GP_LENGTH_M
    radius_m: float = 150.0        # ASSUMED bend radius of the rail
    width_m: float = 25.0          # ASSUMED rail-to-fence width

    @property
    def straight_m(self) -> float:
        s = (self.length_m - 2 * math.pi * self.radius_m) / 2.0
        if s <= 0:
            raise ValueError("radius too large for the lap length")
        return s

    def _segment(self, s: float) -> tuple[int, float]:
        s = s % self.length_m
        S, R = self.straight_m, self.radius_m
        if s < S:
            return 0, s
        if s < S + math.pi * R:
            return 1, s - S
        if s < 2 * S + math.pi * R:
            return 2, s - S - math.pi * R
        return 3, s - 2 * S - math.pi * R

    def rail_point(self, s: float) -> np.ndarray:
        seg, u = self._segment(s)
        S, R = self.straight_m, self.radius_m
        if seg == 0:
            return np.array([-S / 2 + u, -R])
        if seg == 1:
            phi = u / R
            return np.array([S / 2 + R * math.sin(phi), -R * math.cos(phi)])
        if seg == 2:
            return np.array([S / 2 - u, R])
        phi = u / R
        return np.array([-S / 2 - R * math.sin(phi), R * math.cos(phi)])

    def tangent(self, s: float) -> np.ndarray:
        seg, u = self._segment(s)
        R = self.radius_m
        if seg == 0:
            return np.array([1.0, 0.0])
        if seg == 1:
            phi = u / R
            return np.array([math.cos(phi), math.sin(phi)])
        if seg == 2:
            return np.array([-1.0, 0.0])
        phi = u / R
        return np.array([-math.cos(phi), -math.sin(phi)])

    def outward_normal(self, s: float) -> np.ndarray:
        """Away from the infield = to the RIGHT of travel (rail on the left)."""
        t = self.tangent(s)
        return np.array([t[1], -t[0]])

    def point(self, s: float, d: float) -> np.ndarray:
        """Ground point at arc length s along the rail and lateral distance d outward from the rail."""
        return self.rail_point(s) + self.outward_normal(s) * d

    def fence_point(self, s: float) -> np.ndarray:
        return self.point(s, self.width_m)

    def curvature(self, s: float) -> float:
        seg, _ = self._segment(s)
        return 0.0 if seg in (0, 2) else 1.0 / self.radius_m

    def describe(self, s: float) -> str:
        seg, _ = self._segment(s)
        return ("home straight (stands side)", "bend 1", "back straight", "bend 2")[seg]
