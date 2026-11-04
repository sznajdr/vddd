import shutil
import subprocess

import pytest

from tripstate.m0_ingest.video import normalize_video

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.fixture(scope="module")
def clip(tmp_path_factory):
    d = tmp_path_factory.mktemp("src")
    p = d / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "testsrc=size=320x240:rate=30:duration=2", "-pix_fmt", "yuv420p", str(p)], check=True)
    return p


def test_normalize_contract(clip, tmp_path):
    r = normalize_video(clip, tmp_path / "n", 25.0, preset="ultrafast")
    assert not r.ingest_failed, r.reason
    assert (r.width, r.height) == (320, 240)
    assert abs(r.duration_delta_s) <= 1 / 25 + 1e-3
    assert r.producer["interpolation"] == "none" and "ffmpeg" in r.producer["ffmpeg_version"].lower()
    assert (tmp_path / "n" / "normalize.json").exists() and (tmp_path / "n" / "ffprobe_source.json").exists()


def test_idempotent_and_stable_hash(clip, tmp_path):
    a = normalize_video(clip, tmp_path / "n", 25.0, preset="ultrafast")
    b = normalize_video(clip, tmp_path / "n", 25.0, preset="ultrafast")
    assert b.cached and b.normalized_sha256 == a.normalized_sha256
    c = normalize_video(clip, tmp_path / "m", 25.0, preset="ultrafast")  # fresh re-encode, same env
    assert not c.cached and c.normalized_sha256 == a.normalized_sha256


def test_corrupt_source_flags_ingest_failed(tmp_path):
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"\x00\x01garbage" * 1000)
    r = normalize_video(bad, tmp_path / "n", 25.0)
    assert r.ingest_failed and r.reason
    assert not (tmp_path / "n" / "replay.mp4").exists()


def test_missing_source(tmp_path):
    r = normalize_video(tmp_path / "nope.mp4", tmp_path / "n", 25.0)
    assert r.ingest_failed and r.reason == "source_missing_or_empty"
