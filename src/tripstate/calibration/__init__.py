"""Calibration harness (SPEC-2.0.0-draft §7.2; D-18). CODE ONLY until the freeze: `tools/calibrate.py` refuses to
run for real while the spec is DRAFT (D-36); `--synthetic` rehearses the whole loop on synthetic races.

`sidecar`   — stored M4 geometry per race (the `geometry` table's parquet sidecar, JSON here) and its pack-space
              re-derivation (tiers, ranks) under a candidate threshold set — no M2/M3 re-run, ever;
`space`     — the declared search space (`config/calibration/search-space.yaml`): which keys MAY move, over which grid;
`search`    — grid search on dev charts, objective = §6.2 headline, constraints from the TS `calibration` namespace;
`tsio`      — writes `TS-x.y.yaml` with `calibrated: true` and the search provenance (§7.2 step 3, §9 threshold_sets);
`holdout`   — one-shot held-out evaluation and the "> gap → spec revision, not more tuning" rule (§7.2 step 4);
`synthetic` — races built so that only the true thresholds reproduce their hand charts (the dry-run fixture).
"""
from tripstate.calibration.search import (
           CandidateResult,
           DevRace,
           SearchResult,
           evaluate_candidate,
           grid_search,
)
from tripstate.calibration.sidecar import FrameRecord, RaceGeometry, RunnerRecord, rederive
from tripstate.calibration.space import SearchSpace, load_search_space

__all__ = ["CandidateResult", "DevRace", "FrameRecord", "RaceGeometry", "RunnerRecord", "SearchResult", "SearchSpace",
           "evaluate_candidate", "grid_search", "load_search_space", "rederive"]
