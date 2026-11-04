# PILOT-5 — five-race throwaway pilot (freeze evidence; exempt from G-1…G-3)

**Purpose:** produce the numbers the kill-gates KG-2 (tier agreement) and KG-3 (yield) need, plus the human-minutes distribution that instantiates `human_budget_cap_min` and `dod3_median_target_min` (D-29).

**Exemption (RP-2, D-33):** this pilot does not wait for M1–M3 acceptance. It runs whatever gets tracklets on screen. Its outputs carry `producer_kind = pilot_throwaway` and are deleted or quarantined after the freeze. They are never corpus rows, never golden charts, never calibration input.

## Inputs

- 5 races beyond the 3 OD-1x replays, drawn like the eventual golden set (mixed day/night, field sizes, start formats, pistes). None of these 5 may later be a held-out race.
- OD-1x results (EG registry draft values).

## Stack (deliberately minimal; agent-built, 1–2 days)

| Piece | Throwaway choice |
|---|---|
| Shot gating | Manual: the owner marks wide-pan intervals from the coverage sheet. No M1. |
| Detection | Off-the-shelf detector (COCO `horse` class or a zero-shot detector) with boxes expanded to the sulky. No training. |
| Tracking | ByteTrack as shipped with Ultralytics. |
| Seeding | The `tools/seed_cli.py` skeleton: step frames, click runner → type saddle number, log wall-clock. |
| Geometry | `tripstate.m4_geometry.ShotProjector` on the tracked boxes (rail reference clicked once per shot; `ShotCalibration` confirmed by the operator). |
| Labels | Owner hand-labels tier for ≥ 60 frames per race (≥ 300 total) in a CSV: `race_id, frame, saddle_no, tier_human`. |

## Measurements

1. **Human-minutes per race**, full operator loop (§5.1), wall-clock, including re-seeds and anchor clicks. → `human_budget_cap_min` (≈ p90), `dod3_median_target_min` (median), KG-1 corroboration.
2. **Tier agreement**: `tripstate.m4_geometry.cluster_tiers` output vs `tier_human` on the labelled frames, per race and pooled. → KG-2.
3. **`chartable` yield**: apply `tripstate.m7_qc.evaluate_gates` with the OD-1x-instantiated thresholds to each race. Report per stratum. → KG-3, first D-35 numbers.
4. **Anchor residuals** again on 5 more races → tightens KG-4.
5. **Candidate load**: run `tripstate.m6_events.break_candidates` (uncalibrated) and count candidates per race against the hand-noted breaks. Informative only.
6. **Tracker quality**: HOTA/IDF1 of the pre-correction tracks against the operator-corrected result, for both the seeded-propagation path and the detector+BoT-SORT path (research 07, RP-12); frames/s with 14 objects (R-15).

## Output

`data/pilot5/pilot_report.md` with the five numbers, the per-stratum yield table, and a filled `spec/registers/kill_gates.yaml`. Then `make freeze-check`.

## What this pilot does NOT decide

Threshold calibration (§7), module acceptance, DoD-1…6. Those need the golden set, which needs the freeze.
