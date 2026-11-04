# HAND-CHARTING — ground-truth protocol (§5.2; OD-3). **Do not start before the 2.0.0 freeze.**

A hand chart made against a definition that then changes is wasted owner time (D-36). This file exists so the template is ready the day the freeze lands.

## Rules (from §5.2, unchanged)

- Same schema as `state_segments` (§2 / §9), stored as segments.
- Watch at ≤ 1× with pause; apply the same shot gate as M1: outside wide-pan → `SHOT_GAP`, no base state.
- Inside a charted interval, an individually off-screen runner is `NOT_VISIBLE`. Never bridge gaps by inference.
- Breaks: `events` row with `method = human_chart`, `review_status = accepted`, `human_confirmed = true`.
- Record `charter_minutes` per race.
- Dev/held-out split (30/10) fixed in `data/golden/manifest-vX.Y.yaml` **before** charting; `hand_charts.split` is a validated copy (S-6). Held-out races are sealed after charting.

## Golden manifest requirements (§6.1 + 2.0.0)

- 40 races, ≤ 14 runners, mixed day/night, distance bands, `start_format` (≥ 5 dev + ≥ 2 held-out `volte_handicap`), `piste`.
- ≥ 20 observable `BREAK` starts in dev, ≥ 10 in held-out.
- ≥ 10 "boring" races.
- Record selection strata, assignment seed, source hashes.
- The 5 pilot races and the 3 OD-1x races may be **dev** races but never held-out.

## Chart template

`chart_template.csv` columns: `race_id, saddle_no, t_start_frac, t_end_frac, state_kind, state, covered, lead_uncovered_outside, lead_uncovered_outside_ambiguous, tier_attr, end_attr, visibility, start_truncated, end_truncated, notes`.

Fractions use the charter's own `t_0`/`t_end` clicks recorded in `race_anchors` first.
