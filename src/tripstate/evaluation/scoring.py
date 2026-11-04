"""Per-race and per-set scoring on the §6.2 conventions: every metric is averaged over runners, then over races
(D-27 weights for the headline, D-28 rest set). Shared by the calibration harness (§7.2) and the release
evaluation (DoD-1). Masks come from the hand chart's observability (state != NOT_VISIBLE) intersected with the
charted shot intervals; a runner/state with an empty union is omitted, never scored 1."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from tripstate.evaluation.metrics import (
    REST_STATES,
    Interval,
    _norm,
    headline_score,
    is_covered,
    is_uncovered_outside,
    macro_iou,
    mask_iou,
    per_runner_state_iou,
)


@dataclass
class RaceScore:
    race_id: str
    uncovered_outside_iou: float | None
    covered_iou: float | None
    rest_macro: float | None
    per_state: dict[str, float | None] = field(default_factory=dict)
    n_runners: int = 0

    @property
    def headline(self) -> float | None:
        return headline_score(self.uncovered_outside_iou, self.covered_iou, self.rest_macro)


def _mean(xs: Sequence[float | None]) -> float | None:
    v = [x for x in xs if x is not None]
    return sum(v) / len(v) if v else None


def observability_mask(truth_rows: Sequence[dict], charted: Sequence[Interval] | None = None) -> list[Interval]:
    """Time where the hand chart marks the runner observable (any base state but NOT_VISIBLE), clipped to the
    charted shot intervals when given (both in race fraction)."""
    obs = _norm((r["t_start_frac"], r["t_end_frac"]) for r in truth_rows
                if r["state_kind"] == "base" and r["state"] != "NOT_VISIBLE")
    if charted is None:
        return obs
    from tripstate.evaluation.metrics import intersect
    return intersect(obs, charted)


def score_race(race_id: str, pred_rows: Sequence[dict], truth_rows: Sequence[dict],
               charted: Sequence[Interval] | None = None) -> RaceScore:
    saddles = sorted({r["saddle_no"] for r in truth_rows} | {r["saddle_no"] for r in pred_rows})
    uo, cov = [], []
    per_state_runner: dict[str, list[float | None]] = {s: [] for s in REST_STATES}
    for s in saddles:
        p = [r for r in pred_rows if r["saddle_no"] == s]
        t = [r for r in truth_rows if r["saddle_no"] == s]
        mask = observability_mask(t, charted)
        if not mask:
            continue
        uo.append(mask_iou(p, t, mask, is_uncovered_outside))
        cov.append(mask_iou(p, t, mask, is_covered))
        for st in REST_STATES:
            per_state_runner[st].append(per_runner_state_iou(p, t, mask, st))
    per_state = {st: _mean(v) for st, v in per_state_runner.items()}
    return RaceScore(race_id, _mean(uo), _mean(cov), macro_iou(per_state), per_state, len(saddles))


@dataclass
class SetScore:
    n_races: int
    uncovered_outside_iou: float | None
    covered_iou: float | None
    rest_macro: float | None
    per_race: list[RaceScore] = field(default_factory=list)

    @property
    def headline(self) -> float | None:
        return headline_score(self.uncovered_outside_iou, self.covered_iou, self.rest_macro)

    def as_dict(self) -> dict:
        return {"n_races": self.n_races, "uncovered_outside_iou": self.uncovered_outside_iou, "covered_iou": self.covered_iou,
                "rest_macro": self.rest_macro, "headline": self.headline}


def score_set(scores: Sequence[RaceScore]) -> SetScore:
    """Race means of each component (None omitted); the headline is recomputed from the set-level components."""
    return SetScore(len(scores), _mean([s.uncovered_outside_iou for s in scores]), _mean([s.covered_iou for s in scores]),
                    _mean([s.rest_macro for s in scores]), list(scores))
