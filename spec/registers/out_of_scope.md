# Out-of-scope register (2.0.0-draft; extends SPEC-1.2.0 §12)

| Item | Status | Earliest re-entry | Added by |
|---|---|---|---|
| Stretch-block event (`STRETCH_BLOCK`) | Deferred | v1.5 | 1.0.0 |
| Head-on / alternate shot extraction contexts | Deferred | v1.5+ (no stitching) | 1.0.0 |
| Cross-shot identity stitching | Banned | ≥ v3 | 1.0.0 |
| Fully automatic identity (OCR / silk re-ID) | Banned | ≥ v2, trained on accumulated seeding clicks | 1.0.0 |
| Whip, head carriage, driver gaze, fatigue/pose | Banned | ≥ v3 | 1.0.0 |
| Metric ground-loss / homography | Banned | only with GPS/sectional calibration | 1.0.0 |
| Monté | Excluded | separate spec | 1.0.0 |
| Tracks other than Vincennes | Excluded | v2 | 1.0.0 |
| Fields > 14 runners | Excluded (selection bias acknowledged, DR-11; `qc.realization` tag quantifies it) | v2 | 1.0.0 / 2.0.0 |
| Predictive modeling on charts | Out of project boundary | separate project | 1.0.0 |
| Text-comment parsing into the schema | Parallel workstream | — | 1.0.0 |
| **Detached groups** (breakaway pairs) | Deferred | v1.5 | 2.0.0 (F-3) |
| **Move-detection "first over" event** (the horse that first left cover to advance) | Deferred | v1.5 | 2.0.0 (S-1) |
| **Official LeTrot tracking data as source** | To evaluate before P4 | could supersede M2–M4 | 2.0.0 (RP-6) |
| **Landmark / track-position detection** | Banned | reconstruct downstream from `piste` + distance + RK | 2.0.0 (DR-07) |
