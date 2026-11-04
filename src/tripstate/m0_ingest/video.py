"""M0 video normalization (SPEC-2.0.0-draft §4 M0; D-13).

Contract: CFR at `normalized_fps`, source width/height/aspect preserved (no scaling), source +
normalized ffprobe metadata persisted, hashes stable across re-runs in the same environment,
duration within 1 normalized frame of the decoded source, synthetic motion interpolation
forbidden (plain frame drop/dup via the `fps` filter), corrupt/partial files -> ingest_failed,
never silently truncated. Normalization command, ffmpeg version and codec params are returned
for `producer_version`. Idempotent: same source hash -> cached result, no re-encode.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path


@dataclass
class NormalizeResult:
    ingest_failed: bool
    reason: str | None
    source_path: str
    source_sha256: str | None
    normalized_path: str | None
    normalized_sha256: str | None
    normalized_fps: float
    width: int | None
    height: int | None
    source_duration_s: float | None
    normalized_duration_s: float | None
    duration_delta_s: float | None
    cached: bool = False
    producer: dict = field(default_factory=dict)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def ffprobe_json(path: Path, ffprobe: str = "ffprobe") -> dict:
    cmd = [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {p.stderr.strip()[-400:]}")
    return json.loads(p.stdout)


def _video_stream(probe: dict) -> dict | None:
    for s in probe.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    return None


def _duration_s(probe: dict, stream: dict) -> float | None:
    for src in (stream.get("duration"), probe.get("format", {}).get("duration")):
        if src is not None:
            try:
                return float(src)
            except ValueError:
                pass
    return None


def ffmpeg_version(ffmpeg: str = "ffmpeg") -> str:
    p = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, check=False)
    return (p.stdout.splitlines() or ["unknown"])[0]


def normalize_video(
    source: Path,
    out_dir: Path,
    normalized_fps: float,
    *,
    crf: int = 18,
    preset: str = "medium",
    threads: int = 1,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> NormalizeResult:
    source, out_dir = Path(source), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "replay.mp4"
    sidecar = out_dir / "normalize.json"

    def fail(reason: str, src_hash: str | None = None) -> NormalizeResult:
        r = NormalizeResult(True, reason, str(source), src_hash, None, None, normalized_fps,
                            None, None, None, None, None)
        sidecar.write_text(json.dumps(asdict(r), indent=2, sort_keys=True), encoding="utf-8")
        return r

    if not source.exists() or source.stat().st_size == 0:
        return fail("source_missing_or_empty")
    src_hash = sha256_file(source)

    # Idempotency: same source hash + intact output -> cached.
    if sidecar.exists() and out_path.exists():
        try:
            prev = json.loads(sidecar.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
        if (not prev.get("ingest_failed") and prev.get("source_sha256") == src_hash
                and prev.get("normalized_fps") == normalized_fps
                and prev.get("normalized_sha256") == sha256_file(out_path)):
            prev["cached"] = True
            return NormalizeResult(**prev)

    try:
        src_probe = ffprobe_json(source, ffprobe)
    except RuntimeError as e:
        return fail(f"ffprobe_source:{e}", src_hash)
    vs = _video_stream(src_probe)
    if vs is None:
        return fail("no_video_stream", src_hash)
    width, height = int(vs["width"]), int(vs["height"])
    src_dur = _duration_s(src_probe, vs)

    fps_frac = Fraction(normalized_fps).limit_denominator(1001)
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-nostdin", "-loglevel", "error",
        "-i", str(source), "-map", "0:v:0", "-an", "-sn", "-dn",
        "-vf", f"fps=fps={fps_frac.numerator}/{fps_frac.denominator}:round=near", "-fps_mode", "cfr",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-threads", str(threads), "-movflags", "+faststart", str(out_path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0 or not out_path.exists():
        if out_path.exists():
            out_path.unlink()
        return fail(f"ffmpeg_failed:{p.stderr.strip()[-400:]}", src_hash)

    try:
        out_probe = ffprobe_json(out_path, ffprobe)
    except RuntimeError as e:
        return fail(f"ffprobe_output:{e}", src_hash)
    ovs = _video_stream(out_probe) or {}
    out_dur = _duration_s(out_probe, ovs)
    if int(ovs.get("width", -1)) != width or int(ovs.get("height", -1)) != height:
        return fail("dimensions_changed", src_hash)
    delta = None if (src_dur is None or out_dur is None) else out_dur - src_dur
    if delta is not None and abs(delta) > (1.0 / normalized_fps) + 1e-3:
        return fail(f"duration_mismatch:{delta:.4f}s", src_hash)

    r = NormalizeResult(
        ingest_failed=False, reason=None, source_path=str(source), source_sha256=src_hash,
        normalized_path=str(out_path), normalized_sha256=sha256_file(out_path),
        normalized_fps=normalized_fps, width=width, height=height,
        source_duration_s=src_dur, normalized_duration_s=out_dur, duration_delta_s=delta,
        producer={
            "ffmpeg_version": ffmpeg_version(ffmpeg),
            "command": cmd,
            "codec": {"name": "libx264", "preset": preset, "crf": crf, "pix_fmt": "yuv420p", "threads": threads},
            "fps_mode": "cfr", "rate_filter": "fps (drop/dup only)", "interpolation": "none",
        },
    )
    (out_dir / "ffprobe_source.json").write_text(json.dumps(src_probe, indent=1, sort_keys=True), encoding="utf-8")
    (out_dir / "ffprobe_normalized.json").write_text(json.dumps(out_probe, indent=1, sort_keys=True), encoding="utf-8")
    sidecar.write_text(json.dumps(asdict(r), indent=2, sort_keys=True), encoding="utf-8")
    return r
