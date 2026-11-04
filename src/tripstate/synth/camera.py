"""Pinhole broadcast camera (research 11; A1). Image coordinates: x right, y down, origin top-left."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PinholeCamera:
    position: np.ndarray                     # (X, Y, Z) metres, Z up
    image_size: tuple[int, int] = (1920, 1080)
    focal_px: float = 2000.0
    forward: np.ndarray | None = None
    right: np.ndarray | None = None
    down: np.ndarray | None = None

    def look_at(self, target: np.ndarray) -> None:
        f = np.asarray(target, float) - self.position
        f = f / np.linalg.norm(f)
        up = np.array([0.0, 0.0, 1.0])
        r = np.cross(f, up)
        r = r / np.linalg.norm(r)
        self.forward, self.right, self.down = f, r, np.cross(f, r)

    def zoom_to(self, target: np.ndarray, length_m: float, target_px: float) -> None:
        """Set the focal length so a length_m object at the target's depth spans target_px."""
        assert self.forward is not None
        depth = float(np.dot(np.asarray(target, float) - self.position, self.forward))
        self.focal_px = target_px * depth / length_m

    def project(self, points: np.ndarray) -> np.ndarray:
        """points (N, 3) -> (N, 3) of (u, v, depth). Points behind the camera get depth <= 0."""
        assert self.forward is not None
        rel = np.atleast_2d(points) - self.position
        x = rel @ self.right
        y = rel @ self.down
        z = rel @ self.forward
        w, h = self.image_size
        with np.errstate(divide="ignore", invalid="ignore"):
            u = w / 2 + self.focal_px * x / z
            v = h / 2 + self.focal_px * y / z
        return np.stack([u, v, z], axis=1)

    def ground_scale_px_per_m(self, point: np.ndarray, direction: np.ndarray) -> float:
        """Apparent image length (px) of a 1 m ground segment at `point` along unit `direction` (3-D)."""
        p = np.asarray(point, float)
        a, b = self.project(np.stack([p, p + direction]))
        return float(np.hypot(b[0] - a[0], b[1] - a[1]))
