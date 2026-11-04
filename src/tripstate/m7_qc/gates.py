"""QC gates Q-1…Q-7 (SPEC-2.0.0-draft §10; L-41) and per-stratum yield (L-31; D-35)."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from tripstate.config import ThresholdSet

# Closed in v1 (§10). A failed gate MUST append its code; multiple MAY coexist.
FAILURE_CODES = (
    "anchor_missing", "anchor_suspect", "coverage_final_third_low", "coverage_race_low",
    "field_too_large", "graphic_occlusion_high", "id_suspect", "over_budget", "wrong_discipline",
)


@dataclass(frozen=True)
class RaceQCInput:
    coverage_race: float | None           # pack-coherent duration / [t_0, t_end] duration
    coverage_final_third: float | None
    anchors_present: bool
    anchor_suspect: bool
    id_suspect: bool
    pct_graphic_occluded: float
    field_size: int
    discipline: str                       # "attele" expected
    human_minutes: float | None


@dataclass
class GateResult:
    chartable: bool
    failure_codes: list[str] = field(default_factory=list)


def evaluate_gates(inp: RaceQCInput, ts: ThresholdSet) -> GateResult:
    codes: set[str] = set()
    if not inp.anchors_present:
        codes.add("anchor_missing")
    elif inp.anchor_suspect:
        codes.add("anchor_suspect")
    # Q-1 / Q-2: coverage is undefined without anchors (anchor_missing already fails the race);
    # with anchors present an undefined coverage is a pipeline bug, not a gate outcome.
    if inp.anchors_present:
        if inp.coverage_race is None or inp.coverage_final_third is None:
            raise ValueError("coverage fractions must be computed when anchors are present (M7)")
        if inp.coverage_race < float(ts["coverage_race_min"]):
            codes.add("coverage_race_low")
        if inp.coverage_final_third < float(ts["coverage_final_third_min"]):
            codes.add("coverage_final_third_low")
    if inp.id_suspect:
        codes.add("id_suspect")
    if inp.pct_graphic_occluded > float(ts["graphic_occlusion_max"]):
        codes.add("graphic_occlusion_high")
    if inp.field_size > int(ts["max_field_size"]):
        codes.add("field_too_large")
    if inp.discipline != "attele":
        codes.add("wrong_discipline")
    # Q-7: over_budget is not waivable (D-09/D-29). Unknown human_minutes cannot pass the gate.
    if inp.human_minutes is None or inp.human_minutes > float(ts["human_budget_cap_min"]):
        codes.add("over_budget")
    for c in codes:
        assert c in FAILURE_CODES, c
    return GateResult(chartable=not codes, failure_codes=sorted(codes))


def stratum_yield(
    rows: Iterable[tuple[tuple, bool]],
    ts: ThresholdSet,
) -> dict:
    """D-35 per-stratum chartable rate. `rows` = ((stratum tuple), chartable). Stratum tuple =
    (day_night, field_band, start_format, piste). Returns overall rate, per-stratum rates and
    the strata that trip the review trigger (rate < factor x overall)."""
    factor = float(ts["stratum_yield_review_factor"])
    n = defaultdict(int)
    k = defaultdict(int)
    tot_n = tot_k = 0
    for stratum, chartable in rows:
        n[stratum] += 1
        k[stratum] += int(bool(chartable))
        tot_n += 1
        tot_k += int(bool(chartable))
    overall = tot_k / tot_n if tot_n else None
    per = {s: (k[s] / n[s], n[s]) for s in n}
    review = sorted(s for s, (rate, _) in per.items() if overall is not None and rate < factor * overall)
    return {"overall": overall, "per_stratum": per, "review_trigger": review}
