"""Synthetic broadcast: the affine race render cut into shots of different types, a slow-motion replay insert,
a full-screen graphic and a lower-third banner over part of a wide pan — the M1 fixture before any footage."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from tripstate.pilot.frames import PALETTE, encode_frames
from tripstate.synth.race import SynthRace, render_boxes


def _draw_wide(boxes, rail, size, th) -> np.ndarray:
    w, h = size
    sx, sy = w / 1920.0, h / 1080.0
    img = np.full((h, w, 3), 28, np.uint8)
    rx, ry = rail[0] * sx, rail[1] * sy
    for k in range(-w, w):
        x, y = round(rx + k * np.cos(th)), round(ry + k * np.sin(th))
        if 0 <= x < w and 0 <= y < h:
            img[y, x] = (90, 90, 90)
    for b in boxes:
        xa, ya, xb, yb = max(0, int(b.x1 * sx)), max(0, int(b.y1 * sy)), min(w, int(b.x2 * sx)), min(h, int(b.y2 * sy))
        if xb > xa and yb > ya:
            img[ya:yb, xa:xb] = PALETTE[(b.saddle_no - 1) % len(PALETTE)]
    return img


def _tight(img: np.ndarray, boxes, size, scale: int = 3) -> np.ndarray:
    w, h = size
    if not boxes:
        return img
    b = boxes[0]
    cx, cy = int((b.x1 + b.x2) / 2 * w / 1920.0), int((b.y1 + b.y2) / 2 * h / 1080.0)
    hw, hh = w // (2 * scale), h // (2 * scale)
    x0, y0 = min(max(0, cx - hw), w - 2 * hw), min(max(0, cy - hh), h - 2 * hh)
    crop = img[y0:y0 + 2 * hh, x0:x0 + 2 * hw]
    return np.repeat(np.repeat(crop, scale, axis=0), scale, axis=1)[:h, :w]


def _head_on(boxes, size) -> np.ndarray:
    """Runners stacked vertically (approaching the camera): same blobs, vertical spread."""
    w, h = size
    img = np.full((h, w, 3), 28, np.uint8)
    for i, b in enumerate(sorted(boxes, key=lambda b: b.x1)):
        y = int(h * (0.15 + 0.7 * i / max(1, len(boxes) - 1)))
        x = int(w * 0.5 + (b.saddle_no - 4) * w * 0.03)
        img[max(0, y - 8):y + 8, max(0, x - 14):x + 14] = PALETTE[(b.saddle_no - 1) % len(PALETTE)]
    return img


def _graphic(size) -> np.ndarray:
    w, h = size
    img = np.full((h, w, 3), 215, np.uint8)
    for k in range(5):
        y = int(h * (0.2 + 0.14 * k))
        img[y:y + 6, int(w * 0.1):int(w * 0.6)] = (40, 40, 40)
    return img


def render_broadcast(race: SynthRace, out_path: Path, size: tuple[int, int] = (320, 180),
                     script: list[tuple[float, float, str]] | None = None,
                     banner: tuple[float, float] | None = None, replay_source: tuple[float, float] | None = None) -> dict:
    """script: (t_start, t_end, type) contiguous; types wide_pan|tight|head_on|graphic_fullscreen|replay_insert.
    replay_insert replays `replay_source` wide frames at half speed. banner: (t_start, t_end) lower-third over wide pans."""
    fps = race.fps
    rendered = render_boxes(race)
    th = np.radians(race.camera.direction_deg)
    wide = [_draw_wide(boxes, rail, size, th) for _, boxes, rail in rendered]
    n = len(wide)
    script = script or [(0.0, n / fps, "wide_pan")]
    frames: list[np.ndarray] = []
    truth_shots: list[tuple[float, float, str]] = []
    for a, b, typ in script:
        ia, ib = round(a * fps), round(b * fps)
        seg: list[np.ndarray] = []
        if typ == "wide_pan":
            seg = [wide[i].copy() for i in range(ia, ib)]
        elif typ == "tight":
            seg = [_tight(wide[i], rendered[i][1], size) for i in range(ia, ib)]
        elif typ == "head_on":
            seg = [_head_on(rendered[i][1], size) for i in range(ia, ib)]
        elif typ == "graphic_fullscreen":
            seg = [_graphic(size) for _ in range(ia, ib)]
        elif typ == "replay_insert":
            sa, sb = replay_source or (0.0, (b - a) / 2)
            src = [wide[i] for i in range(round(sa * fps), round(sb * fps))]
            seg = [src[min(len(src) - 1, (i - ia) // 2)].copy() for i in range(ia, ib)]
            for k in range(min(2, len(seg))):          # wipe
                seg[k][:, : size[0] // 3] = 230
        else:
            raise ValueError(typ)
        if banner and typ == "wide_pan":
            for i in range(ia, ib):
                if banner[0] <= i / fps < banner[1]:
                    img = seg[i - ia]
                    img[int(size[1] * 0.8):int(size[1] * 0.95), int(size[0] * 0.1):int(size[0] * 0.9)] = (235, 235, 235)
        frames.extend(seg)
        truth_shots.append((ia / fps, ib / fps, typ))
    encode_frames(frames, out_path, fps)
    return {"fps": fps, "size": list(size), "shots": truth_shots, "banner": banner, "n_frames": len(frames)}
