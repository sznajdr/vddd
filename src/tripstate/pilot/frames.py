"""Frame I/O through ffmpeg pipes (no OpenCV dependency) and a synthetic-video renderer."""
from __future__ import annotations

import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from tripstate.m0_ingest.video import ffprobe_json
from tripstate.m4_geometry.projection import Box
from tripstate.synth.race import SynthRace, render_boxes


class FrameSource:
    """Sequential RGB frames from a video via `ffmpeg -f rawvideo`. `scale=(w, h)` resizes."""

    def __init__(self, path: Path, scale: tuple[int, int] | None = None, ffmpeg: str = "ffmpeg"):
        self.path = Path(path)
        self.ffmpeg = ffmpeg
        probe = ffprobe_json(self.path)
        vs = next(s for s in probe["streams"] if s["codec_type"] == "video")
        num, den = (int(x) for x in vs["r_frame_rate"].split("/"))
        self.fps = num / den
        self.src_size = (int(vs["width"]), int(vs["height"]))
        self.size = scale or self.src_size
        nb = vs.get("nb_frames")
        self.n_frames = int(nb) if nb else round(float(vs.get("duration") or probe["format"]["duration"]) * self.fps)
        self._cache: list[np.ndarray] | None = None

    def __iter__(self) -> Iterator[tuple[int, float, np.ndarray]]:
        w, h = self.size
        cmd = [self.ffmpeg, "-v", "error", "-nostdin", "-i", str(self.path), "-f", "rawvideo", "-pix_fmt", "rgb24"]
        if self.size != self.src_size:
            cmd += ["-vf", f"scale={w}:{h}"]
        cmd += ["-"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        assert p.stdout is not None
        n = w * h * 3
        i = 0
        try:
            while True:
                buf = p.stdout.read(n)
                if len(buf) < n:
                    break
                yield i, i / self.fps, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
                i += 1
        finally:
            p.stdout.close()
            p.wait()

    def frame_cache(self) -> list[np.ndarray]:
        if self._cache is None:
            self._cache = [f for _, _, f in self]
            self.n_frames = len(self._cache)
        return self._cache


def encode_frames(frames: list[np.ndarray], path: Path, fps: float, crf: int = 18, ffmpeg: str = "ffmpeg") -> Path:
    h, w, _ = frames[0].shape
    cmd = [ffmpeg, "-y", "-v", "error", "-nostdin", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-preset", "ultrafast", "-crf", str(crf), "-pix_fmt", "yuv420p", str(path)]
    p = subprocess.run(cmd, input=b"".join(np.ascontiguousarray(f, dtype=np.uint8).tobytes() for f in frames), capture_output=True, check=False)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode()[-400:])
    return Path(path)


PALETTE = [(255, 80, 80), (80, 255, 80), (80, 120, 255), (255, 255, 80), (255, 80, 255), (80, 255, 255),
           (255, 160, 80), (200, 200, 200), (160, 80, 255), (80, 200, 160), (255, 120, 160), (160, 255, 80),
           (120, 160, 255), (255, 200, 200)]


def render_synth_video(race: SynthRace, out_path: Path, size: tuple[int, int] = (640, 360), crf: int = 18) -> dict:
    """Draw the synthetic race (filled runner rectangles, a thin rail line) and encode it. Returns
    truth in the rendered pixel space: {'fps', 'size', 'scale', 'boxes': {frame: {saddle: [x1,y1,x2,y2]}}, 'rail': {frame: [x, y]}}."""
    w, h = size
    sx, sy = w / 1920.0, h / 1080.0
    frames: list[np.ndarray] = []
    truth_boxes: dict[int, dict[int, list[float]]] = {}
    rail_pts: dict[int, list[float]] = {}
    th = np.radians(race.camera.direction_deg)
    for i, (t, boxes, rail) in enumerate(render_boxes(race)):
        img = np.full((h, w, 3), 28, np.uint8)
        rx, ry = rail[0] * sx, rail[1] * sy
        for k in range(-w, w):  # rail line through the rail reference point along the travel direction
            x, y = round(rx + k * np.cos(th)), round(ry + k * np.sin(th))
            if 0 <= x < w and 0 <= y < h:
                img[y, x] = (90, 90, 90)
        tb: dict[int, list[float]] = {}
        for b in boxes:
            x1, y1, x2, y2 = b.x1 * sx, b.y1 * sy, b.x2 * sx, b.y2 * sy
            xa, ya, xb, yb = max(0, int(x1)), max(0, int(y1)), min(w, int(x2)), min(h, int(y2))
            if xb > xa and yb > ya:
                img[ya:yb, xa:xb] = PALETTE[(b.saddle_no - 1) % len(PALETTE)]
            tb[b.saddle_no] = [x1, y1, x2, y2]
        truth_boxes[i] = tb
        rail_pts[i] = [rx, ry]
        frames.append(img)
    encode_frames(frames, out_path, race.fps, crf)
    truth = {"fps": race.fps, "size": [w, h], "scale": [sx, sy], "t0": race.t0, "tend": race.tend,
             "saddles": [r.saddle_no for r in race.runners],
             "boxes": {str(k): {str(s): v for s, v in d.items()} for k, d in truth_boxes.items()},
             "rail": {str(k): v for k, v in rail_pts.items()}}
    Path(str(out_path) + ".truth.json").write_text(json.dumps(truth), encoding="utf-8")
    return truth


def truth_boxes_from_json(truth: dict) -> dict[int, dict[int, Box]]:
    return {int(k): {int(s): Box(int(s), *v) for s, v in d.items()} for k, d in truth["boxes"].items()}
