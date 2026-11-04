"""§7.2 step 2: grid search over the declared keys against DEV hand charts.

Objective: the §6.2 weighted headline (D-27 weights, D-28 rest set), averaged over runners then races.
Constraints (from the threshold set's `calibration` namespace — numbers are config, D-18): both mask IoUs at or
above their floors and the M6 candidate load (per M6-evaluable attempt, median) at or below its cap. A candidate
threshold set is evaluated by re-deriving tiers from the stored M4 geometry and re-running M5 (`chart_race`),
and — when the sidecar carries box heights — the M6 reference detector for the load; M2/M3 never run here.
Ties resolve to the first candidate in grid order (deterministic, D-32)."""
from __future__ import annotations

import itertools
import statistics as st
from dataclasses import dataclass, field, replace
from typing import Any

from tripstate.calibration.sidecar import RaceGeometry, rederive
from tripstate.config import Threshold, ThresholdSet
from tripstate.evaluation.scoring import RaceScore, SetScore, score_race, score_set
from tripstate.m5_states.smoothing import chart_race


@dataclass
class DevRace:
    race_id: str
    geometry: RaceGeometry
    hand_chart: list[dict]          # hand_charts-shaped rows (segment payload), this race only
    split: str = "dev"


@dataclass
class CandidateResult:
    overrides: dict[str, Any]
    score: SetScore
    candidate_load_median: float | None        # None = not evaluable (no box series in the sidecars)
    violations: list[str] = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not self.violations

    @property
    def headline(self) -> float | None:
        return self.score.headline

    def as_dict(self) -> dict:
        return {"overrides": self.overrides, **self.score.as_dict(), "candidate_load_median": self.candidate_load_median,
                "feasible": self.feasible, "violations": self.violations}


@dataclass
class SearchResult:
    space: dict[str, list]
    objective: str
    constraints: dict[str, float]
    results: list[CandidateResult]
    best: CandidateResult | None
    reasons: list[str] = field(default_factory=list)     # why there is no best, when there is none

    def as_dict(self) -> dict:
        return {"space": self.space, "objective": self.objective, "constraints": self.constraints,
                "n_candidates": len(self.results), "best": self.best.as_dict() if self.best else None,
                "reasons": self.reasons, "results": [r.as_dict() for r in self.results]}


def candidate_ts(base: ThresholdSet, overrides: dict[str, Any]) -> ThresholdSet:
    """A copy of `base` with the given keys replaced (values only; namespaces and flags unchanged)."""
    th = dict(base.thresholds)
    for k, v in overrides.items():
        if k not in th:
            raise KeyError(f"threshold {k!r} not in {base.version}")
        th[k] = Threshold(k, th[k].namespace, v, th[k].eg, th[k].used_in)
    return replace(base, thresholds=th)


def constraints_of(ts: ThresholdSet) -> dict[str, float]:
    return {"uncovered_outside_iou_floor": float(ts["uncovered_outside_iou_floor"]),
            "covered_iou_floor": float(ts["covered_iou_floor"]),
            "candidate_load_median_max": float(ts["candidate_load_median_max"])}


def _frac_intervals(geom: RaceGeometry) -> list[tuple[float, float]]:
    d = geom.tend_video_s - geom.t0_video_s
    return [((a - geom.t0_video_s) / d, (b - geom.t0_video_s) / d) for a, b in geom.intervals]


def chart_under(ts: ThresholdSet, geom: RaceGeometry) -> tuple[list[dict], dict[int, list[int | None]], list[float]]:
    frames, times, ranks = rederive(geom, ts)
    rows = chart_race(frames, times, geom.intervals, geom.t0_video_s, geom.tend_video_s, ts)
    return rows, ranks, times


def candidate_load(ts: ThresholdSet, geom: RaceGeometry, ranks: dict[int, list[int | None]], times: list[float]) -> int | None:
    """Number of M6 candidates for this attempt (all runners), or None when the sidecar has no box series."""
    from tripstate.m6_events.breaks import break_candidates

    sl = [f.sl_px for f in geom.frames]
    if any(v is None for v in sl):
        return None
    n = 0
    for s in geom.saddles:
        h = [f.runners[s].box_h_px if s in f.runners else None for f in geom.frames]
        if all(v is None for v in h):
            return None
        n += len(break_candidates(times, ranks[s], h, sl, ts))
    return n


def score_candidate(ts: ThresholdSet, races: list[DevRace]) -> tuple[list[RaceScore], float | None]:
    scores, loads = [], []
    for r in races:
        rows, ranks, times = chart_under(ts, r.geometry)
        scores.append(score_race(r.race_id, rows, r.hand_chart, _frac_intervals(r.geometry)))
        loads.append(candidate_load(ts, r.geometry, ranks, times))
    load_med = None if any(v is None for v in loads) or not loads else float(st.median(loads))
    return scores, load_med


def evaluate_candidate(base: ThresholdSet, overrides: dict[str, Any], races: list[DevRace],
                       constraints: dict[str, float] | None = None) -> CandidateResult:
    cons = constraints or constraints_of(base)
    ts = candidate_ts(base, overrides)
    scores, load_med = score_candidate(ts, races)
    set_score = score_set(scores)
    v = []
    if set_score.uncovered_outside_iou is None or set_score.uncovered_outside_iou < cons["uncovered_outside_iou_floor"]:
        v.append(f"uncovered-outside IoU {set_score.uncovered_outside_iou} < floor {cons['uncovered_outside_iou_floor']}")
    if set_score.covered_iou is None or set_score.covered_iou < cons["covered_iou_floor"]:
        v.append(f"covered IoU {set_score.covered_iou} < floor {cons['covered_iou_floor']}")
    if load_med is not None and load_med > cons["candidate_load_median_max"]:
        v.append(f"candidate load median {load_med} > {cons['candidate_load_median_max']}")
    return CandidateResult(dict(overrides), set_score, load_med, v)


def grid_search(base: ThresholdSet, space: dict[str, list], races: list[DevRace],
                constraints: dict[str, float] | None = None, progress=None) -> SearchResult:
    """Exhaustive grid in declaration order. Best = highest headline among feasible candidates; ties → first."""
    if not races:
        raise ValueError("no dev races")
    if any(r.split != "dev" for r in races):
        raise ValueError("grid search runs on dev races only (§7.2 step 1 / §5.2 sealed held-out)")
    cons = constraints or constraints_of(base)
    keys = list(space)
    results: list[CandidateResult] = []
    for combo in itertools.product(*(space[k] for k in keys)):
        res = evaluate_candidate(base, dict(zip(keys, combo)), races, cons)
        results.append(res)
        if progress:
            progress(len(results), res)
    feasible = [r for r in results if r.feasible and r.headline is not None]
    best = max(feasible, key=lambda r: r.headline) if feasible else None   # max keeps the first on ties
    reasons = [] if best else [("no candidate satisfies the §7.2 constraints on the dev set; the state definitions, not the "
                                "thresholds, are suspect — open a spec revision rather than widening the grid")]
    return SearchResult({k: list(v) for k, v in space.items()}, "headline_score", cons, results, best, reasons)
