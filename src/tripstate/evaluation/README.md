# evaluation — §6.2 metrics and §6.4 identity audit

Pure functions over segment rows: Segment IoU with visibility mask, covered and uncovered-outside mask IoUs, macro IoU, headline score (D-27 weights), Wilson CI (D-31), one-to-one break matching, descriptive edit score and F1@k (RP-14); stratified audit sampler with seeded RNG, effective-n warning and operating characteristic (L-33). `scoring.py`: per-race / per-set aggregation on the §6.2 convention (runners, then races) with the observability mask from the hand chart; shared by the calibration harness and the DoD evaluation.
