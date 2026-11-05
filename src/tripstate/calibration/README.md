# calibration — §7.2 harness (D-18). Code only until the freeze (D-36).

**Spec:** §7.2 steps 1–5, §6.2 headline (D-27/D-28), §9 `threshold_sets.search_provenance`. **Status:** grid search, provenance writer, held-out gap rule and synthetic dry run implemented and tested; `tools/calibrate.py` refuses to run for real while `SPEC_STATUS = DRAFT` or without a golden manifest, and never searches an evidence-gated key.

| | |
|---|---|
| Input | Per dev race: a `geometry` sidecar (`RaceGeometry`: per frame per runner `l_sl`, `w_sw`, conf, detection, rail reference, box height) + the hand chart (segment payload, `split = dev`); the declared space `config/calibration/search-space.yaml`; constraints from the TS `calibration` namespace. |
| Output | `TS-x.y.yaml` with `calibrated: true` and `search_provenance` (space, objective, constraints, best score/components, dev races, seed, date, base set); `*.search.json`; with `--heldout` once: `*.heldout.json` + a §14 changelog row draft and the verdict `accept` / `spec_revision`. |
| Acceptance | `tests/test_calibration.py`: the sidecar re-derivation reproduces the projector's tiers and ranks exactly; a deliberately mis-set `cover_lat_sw` / `same_tier_sw` is recovered within one grid step (the optimum is strict); held-out races are refused by the search; provenance round-trips through `ThresholdSet.load`; the > 10 pt dev/held-out gap yields `spec_revision`. |
| DoD | Candidate evaluation re-runs only pack-space tiering + M5 (and the M6 reference detector for the load constraint) on stored geometry — never M2/M3; ties resolve to grid order (D-32); no feasible candidate → no threshold set is written. |

Rehearsal: `make calibrate-dry-run` (`tools/calibrate.py --synthetic`). Real use, after the freeze and the golden manifest: `tools/export_calibration_inputs.py` (C8) writes `data/calibration/` from the pipeline's per-race frame JSON (`tripstate.m4_geometry.frames_to_json`), the store's `hand_charts` and the manifest, refusing S-6 mismatches and ambiguous human producers; then `tools/calibrate.py` as in its docstring.
