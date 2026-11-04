"""§6.4 identity audit, 2.0.0 form (L-33; D-31).

12 timestamps stratified across 4 phase bins of [t_0, t_end] (3 per bin), 3 visible runners resampled
per timestamp without replacement where possible, RNG seed = SHA-256(race_id | extractor_version |
"identity-audit-v1"). Pass = >= 35/36 correct. The sampled points MUST touch >= 8 distinct tracklet
intervals or the audit reports its effective n. Operating characteristic: P(pass | per-sample accuracy p).
"""
from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field


@dataclass
class AuditPlan:
    seed: int
    points: list[tuple[float, int]]            # (t_video_s, saddle_no)
    tracklet_ids: list[object]                 # tracklet interval id per point (as given by the caller)
    effective_n: int
    warnings: list[str] = field(default_factory=list)


def audit_seed(race_id: str, extractor_version: str) -> int:
    h = hashlib.sha256(f"{race_id}|{extractor_version}|identity-audit-v1".encode()).hexdigest()
    return int(h[:16], 16)


def plan_audit(
    race_id: str,
    extractor_version: str,
    t0: float,
    tend: float,
    visible_runners_at: Callable[[float], Sequence[int]],
    tracklet_of: Callable[[int, float], object],
    n_timestamps: int = 12,
    runners_per_t: int = 3,
    bins: int = 4,
    min_tracklets: int = 8,
) -> AuditPlan:
    rng = random.Random(audit_seed(race_id, extractor_version))
    per_bin = n_timestamps // bins
    ts_list: list[float] = []
    width = (tend - t0) / bins
    for b in range(bins):
        lo = t0 + b * width
        for _ in range(per_bin):
            ts_list.append(lo + rng.random() * width)
    ts_list.sort()
    points: list[tuple[float, int]] = []
    tids: list[object] = []
    warnings: list[str] = []
    for t in ts_list:
        vis = sorted(set(visible_runners_at(t)))
        if not vis:
            warnings.append(f"no visible runner at t={t:.2f}")
            continue
        chosen = rng.sample(vis, min(runners_per_t, len(vis)))
        if len(chosen) < runners_per_t:
            warnings.append(f"only {len(chosen)} visible at t={t:.2f}")
        for s in sorted(chosen):
            points.append((t, s))
            tids.append(tracklet_of(s, t))
    eff = len(set(tids))
    if eff < min_tracklets:
        warnings.append(f"effective n = {eff} distinct tracklet intervals (< {min_tracklets}); audit is weaker than its nominal 36 samples")
    return AuditPlan(audit_seed(race_id, extractor_version), points, tids, eff, warnings)


def pass_probability(p: float, n: int = 36, min_correct: int = 35) -> float:
    """P(>= min_correct of n correct) under independence with per-sample accuracy p."""
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(min_correct, n + 1))


def score_audit(results: Sequence[bool], n_required: int = 36, min_correct: int = 35) -> dict:
    n = len(results)
    k = sum(1 for r in results if r)
    return {"n": n, "correct": k, "pass": n >= n_required and k >= min_correct, "rate": (k / n) if n else None}
