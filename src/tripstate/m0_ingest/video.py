"""M0 video normalization — STUB (needs ffmpeg + replays; blocked on OD-1x sourcing).

Contract (§4 M0): CFR at `normalized_fps`, source width/height/aspect preserved, source +
normalized ffprobe metadata persisted, hashes stable across re-runs, duration within 1
normalized frame of decoded source, synthetic motion interpolation forbidden, corrupt/partial
files -> ingest_failed. Normalization command, ffmpeg build hash and codec params recorded
under producer_version.
"""
from __future__ import annotations

from pathlib import Path


def normalize_video(source: Path, out_dir: Path, normalized_fps: float) -> dict:
    raise NotImplementedError("M0 video normalization: SPEC-2.0.0-draft §4 M0; needs replays (OD-1x)")
