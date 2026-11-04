"""Stored M4 geometry ("geometry" sidecar, §9) and its re-derivation under another threshold set.

What is stored is what M2–M4 measured and cannot be changed by calibration: per frame, per runner, the pack-space
coordinates `l_sl` / `w_sw`, the projection confidence, detection presence, the rail reference (`rail_ref_w_sw`,
`rail_ref_conf`), plus the box height and SL in pixels for the M6 signals. What is re-derived under a candidate
threshold set is everything §2.2 defines from those numbers: clusters, absolute tiers (`same_tier_sw`,
`max_tier_span_sw`, rail attachment) and longitudinal ranks. M5 (`chart_race`) then runs on the re-derived frames.
Floats are stored unquantized (operational artifact; the canonical export quantizes, D-32)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from tripstate.config import ThresholdSet
from tripstate.m4_geometry.tiering import absolute_tiers, cluster_tiers
from tripstate.m5_states.smoothing import FrameGeom


@dataclass
class RunnerRecord:
    detected: bool
    conf: float
    l_sl: float | None = None
    w_sw: float | None = None
    box_h_px: float | None = None


@dataclass
class FrameRecord:
    t: float
    rail_ref_w_sw: float | None
    rail_ref_conf: float | None
    sl_px: float | None
    runners: dict[int, RunnerRecord] = field(default_factory=dict)


@dataclass
class RaceGeometry:
    race_id: str
    t0_video_s: float
    tend_video_s: float
    intervals: list[tuple[float, float]]          # charted wide-pan intervals, video seconds
    saddles: list[int]
    frames: list[FrameRecord]
    producer: str = ""                             # e.g. "ShotProjector/TS-0.0.0-provisional" or "synthetic"

    @property
    def times(self) -> list[float]:
        return [f.t for f in self.frames]

    def to_json(self) -> str:
        d = asdict(self)
        for f in d["frames"]:
            f["runners"] = {str(k): v for k, v in f["runners"].items()}
        return json.dumps(d, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_json(cls, text: str) -> RaceGeometry:
        d = json.loads(text)
        frames = [FrameRecord(f["t"], f["rail_ref_w_sw"], f["rail_ref_conf"], f["sl_px"],
                              {int(k): RunnerRecord(**v) for k, v in f["runners"].items()}) for f in d["frames"]]
        return cls(d["race_id"], d["t0_video_s"], d["tend_video_s"], [tuple(iv) for iv in d["intervals"]], list(d["saddles"]),
                   frames, d.get("producer", ""))

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_projector(cls, race_id: str, frames, saddles: list[int], t0: float, tend: float,
                       intervals: list[tuple[float, float]], box_heights: dict[float, dict[int, float]] | None = None,
                       sl_px: dict[float, float] | None = None, producer: str = "ShotProjector") -> RaceGeometry:
        """From M4 `FrameGeometry` objects (tripstate.m4_geometry.projection)."""
        recs = []
        for f in frames:
            by = {r.saddle_no: r for r in f.runners}
            rail_w = next((r.rail_ref_w_sw for r in f.runners if r.rail_ref_w_sw is not None), None)
            rail_c = next((r.rail_ref_conf for r in f.runners if r.rail_ref_conf is not None), None)
            runners = {}
            for s in saddles:
                r = by.get(s)
                h = (box_heights or {}).get(f.t, {}).get(s)
                if r is None or not r.detected:
                    runners[s] = RunnerRecord(False, 0.0, None, None, h)
                else:
                    runners[s] = RunnerRecord(True, float(r.conf), r.l_sl, r.w_sw, h)
            recs.append(FrameRecord(f.t, rail_w, rail_c, (sl_px or {}).get(f.t, f.sl_px), runners))
        return cls(race_id, t0, tend, list(intervals), list(saddles), recs, producer)


def rederive(geom: RaceGeometry, ts: ThresholdSet) -> tuple[dict[int, list[FrameGeom]], list[float], dict[int, list[int | None]]]:
    """Pack-space re-derivation under `ts`: {saddle: [FrameGeom]} aligned with times (M5 input), plus per-runner
    longitudinal ranks (M6 input). Degenerate frames (no coordinates) stay conf-as-stored with tier None."""
    frames: dict[int, list[FrameGeom]] = {s: [] for s in geom.saddles}
    ranks: dict[int, list[int | None]] = {s: [] for s in geom.saddles}
    for f in geom.frames:
        valid = {s: r for s, r in f.runners.items() if r.detected and r.conf > 0 and r.l_sl is not None and r.w_sw is not None}
        w = {s: float(r.w_sw) for s, r in valid.items()}   # type: ignore[arg-type]
        l = {s: float(r.l_sl) for s, r in valid.items()}   # type: ignore[arg-type]
        saddles = sorted(valid)
        tiers: dict[int, int | None] = {}
        if saddles:
            clusters = cluster_tiers([w[s] for s in saddles], saddles, ts)
            tiers = absolute_tiers(clusters, w, f.rail_ref_w_sw, f.rail_ref_conf, ts)
        order = sorted(saddles, key=lambda s: (-l[s], s))
        rank = {s: i + 1 for i, s in enumerate(order)}
        for s in geom.saddles:
            r = f.runners.get(s)
            if r is None or not r.detected:
                frames[s].append(FrameGeom(f.t, False, 0.0))
                ranks[s].append(None)
            else:
                frames[s].append(FrameGeom(f.t, True, float(r.conf), r.l_sl, r.w_sw, tiers.get(s)))
                ranks[s].append(rank.get(s))
    return frames, geom.times, ranks
