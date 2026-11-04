"""M6 break candidates — STUB (SPEC-2.0.0-draft §4 M6, §2.5; L-15, L-16, L-26).

Signal = longitudinal-rank velocity anomaly + bbox vertical-oscillation regime change (config-exposed
under namespace `m6_events`). Candidates start `review_status = pending`. Accepted + known end ->
BREAKING overlay; unobservable end -> t_end_frac NULL, overlay end_truncated. A break open at
t_frac = 1.0 -> t_end_frac NULL, recovered NULL (DR-10) — never "fixed".
positions_lost only when the visible set is identical at both samples, else NULL; record
positions_lost_basis_n (F-7). DAI cross-check tags: dai_uncaught_break_expected | dai_gait_other;
calibration MUST NOT tune against dai_gait_other (DR-09).
Acceptance: candidate recall >= 0.80 (point estimate + Wilson CI reported, D-31); candidate load
<= 4 per M6-evaluable attempt median.
"""


def positions_lost(rank_before: int | None, rank_after: int | None,
                   visible_before: frozenset[int], visible_after: frozenset[int]) -> tuple[int | None, int | None]:
    """F-7 strict form. Returns (positions_lost, basis_n). Pure; implemented now."""
    if rank_before is None or rank_after is None or visible_before != visible_after:
        return None, None
    return rank_after - rank_before, len(visible_before)


def break_candidates(*args, **kwargs):
    raise NotImplementedError("M6: SPEC-2.0.0-draft §4 M6; needs M4 series + M2 bbox series")
