"""M0 metadata normalization (SPEC-2.0.0-draft §4 M0, rules 1–6; D-22, D-24; S-3, S-5, DR-04, DR-06).

Pure functions. No I/O. Thresholds come from a ThresholdSet. Unit guessing is fabrication.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from tripstate.config import ThresholdSet

# Closed, lex-sorted set (rule 6). Extensions = minor bump.
CONFLICT_CODES = (
    "elapsed_implausible",
    "elapsed_is_km_rate",
    "km_rate_implausible",
    "rendement_not_25m",
    "time_fields_disagree",
)

StartType = Literal["volte", "autostart"]
StartFormat = Literal["autostart", "volte_flat", "volte_handicap"]
Piste = Literal["GP", "PP"]
TimeStatus = Literal["direct_elapsed", "km_rate_derived", "unavailable"]


@dataclass(frozen=True)
class RunnerIn:
    saddle_no: int
    distance_run_m: int | None
    official_elapsed_s: float | None = None
    official_km_rate_s: float | None = None
    raw_elapsed_str: str | None = None
    raw_km_rate_str: str | None = None
    autostart_row: int | None = None  # DR-04: 1, 2 or None
    official_status: str | None = None  # e.g. DAI, DQ, NP


@dataclass(frozen=True)
class RaceIn:
    race_id: str
    base_distance_m: int
    start_type: StartType
    start_format: StartFormat
    runners: tuple[RunnerIn, ...]
    piste: Piste | None = None  # DR-06: from ingest only, never inferred from distance


@dataclass
class RunnerNorm:
    saddle_no: int
    distance_run_m: int
    rendement_m: int
    time_normalization_status: TimeStatus
    official_elapsed_norm_s: float | None
    conflict_codes: list[str] = field(default_factory=list)
    autostart_row: int | None = None


@dataclass
class RaceNorm:
    race_id: str
    ingest_failed: bool
    failure_reasons: list[str]
    start_handicap: bool
    piste: Piste | None
    runners: list[RunnerNorm]
    metadata_conflict_codes: list[str]


def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def normalize_runner_time(
    elapsed_s: float | None,
    km_rate_s: float | None,
    distance_run_m: int,
    ts: ThresholdSet,
) -> tuple[TimeStatus, float | None, list[str]]:
    """Rule 4 + rule 5. Returns (status, official_elapsed_norm_s, conflict_codes).

    Branch 4 statuses per S-3: elapsed-only + plausible -> direct_elapsed;
    km-rate-only + plausible -> km_rate_derived.
    """
    tol = float(ts["time_unit_consistency_tol_s"])
    kmin = float(ts["plausible_km_rate_min_s"])
    kmax = float(ts["plausible_km_rate_max_s"])
    codes: list[str] = []

    if elapsed_s is not None and km_rate_s is not None:
        derived = km_rate_s * distance_run_m / 1000.0
        if _close(elapsed_s, derived, tol):
            return "direct_elapsed", float(elapsed_s), codes
        if _close(elapsed_s, km_rate_s, tol):
            codes.append("elapsed_is_km_rate")
            return "km_rate_derived", derived, codes
        codes.append("time_fields_disagree")
        return "unavailable", None, codes

    if elapsed_s is not None:
        implied = elapsed_s * 1000.0 / distance_run_m
        if kmin <= implied <= kmax:
            return "direct_elapsed", float(elapsed_s), codes
        codes.append("elapsed_implausible")
        return "unavailable", None, codes

    if km_rate_s is not None:
        if kmin <= km_rate_s <= kmax:
            return "km_rate_derived", km_rate_s * distance_run_m / 1000.0, codes
        codes.append("km_rate_implausible")
        return "unavailable", None, codes

    return "unavailable", None, codes  # no field: expected for NP/DAI/unresulted, no code


def normalize_race(race: RaceIn, ts: ThresholdSet) -> RaceNorm:
    """Rules 1–6 for a whole race. ingest_failed on any hard invariant violation; inference is banned."""
    reasons: list[str] = []
    race_codes: set[str] = set()
    runners: list[RunnerNorm] = []

    # Rule 2 — start-format invariants (checked after per-runner distances are known).
    if (race.start_type == "autostart") != (race.start_format == "autostart"):
        reasons.append("start_type_vs_start_format")

    if race.piste is not None and race.piste not in ("GP", "PP"):
        reasons.append("piste_invalid")

    any_positive_rendement = False
    for r in race.runners:
        # Rule 1 — distances.
        if r.distance_run_m is None or r.distance_run_m < race.base_distance_m:
            reasons.append(f"distance_missing_or_below_base:{r.saddle_no}")
            continue
        rendement = r.distance_run_m - race.base_distance_m
        codes: list[str] = []
        if rendement % 25 != 0:
            codes.append("rendement_not_25m")
        if rendement > 0:
            any_positive_rendement = True

        # DR-04 — autostart_row domain.
        if r.autostart_row not in (None, 1, 2):
            reasons.append(f"autostart_row_invalid:{r.saddle_no}")

        # Rules 4–5 — time normalization, independent of first-past resolution.
        status, norm, tcodes = normalize_runner_time(
            r.official_elapsed_s, r.official_km_rate_s, r.distance_run_m, ts
        )
        codes.extend(tcodes)
        codes = sorted(set(codes))
        race_codes.update(codes)
        runners.append(
            RunnerNorm(
                saddle_no=r.saddle_no,
                distance_run_m=r.distance_run_m,
                rendement_m=rendement,
                time_normalization_status=status,
                official_elapsed_norm_s=norm,
                conflict_codes=codes,
                autostart_row=r.autostart_row,
            )
        )

    if race.start_format in ("autostart", "volte_flat") and any_positive_rendement:
        reasons.append("rendement_in_non_handicap")
    if race.start_format == "volte_handicap" and not any_positive_rendement:
        reasons.append("handicap_without_rendement")

    for c in race_codes:
        if c not in CONFLICT_CODES:  # closed set, rule 6
            raise ValueError(f"unknown conflict code {c!r}")

    return RaceNorm(
        race_id=race.race_id,
        ingest_failed=bool(reasons),
        failure_reasons=reasons,
        start_handicap=(race.start_format == "volte_handicap"),
        piste=race.piste,
        runners=runners,
        metadata_conflict_codes=sorted(race_codes),
    )
