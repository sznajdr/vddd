# Handoff — continue implementation

Updated 2026-11-04. Governing version: SPEC-2.0.0-draft. Work on PR #1, claude/elegant-newton-4ex3kg into main. Fetch first and preserve concurrent commits: Claude is also watching this PR.

The owner delegated the outstanding design decisions. The old D1 approval queue is complete; do not wait for another sign-off. Read CLAUDE.md, docs/decisions/2026-11-04-continuation.md, STATUS.md and the generated draft.

## Applied decisions and cleanup

- RP-11: the front tier-1 runner remains LEADER even with outside cover; covered is independent. Table, invariant, implementation and fixture agree.
- stratum_yield_review_factor remains ordinary versioned review-policy config. Its two EG markers and YAML flag are removed. The synthetic-only registry workaround is removed.
- RP-19/20/21/22/23: accept opt-in rail axis, projective lateral scale, local polyline datum and foot correction. Explicit section 3.3 carve-out; no homography or landmark inference. Keep reproducible motion/sw_ratio defaults until replay evidence supports enabling alternatives. Degenerate/unresolved geometry abstains under EC-13. RP-24/25 new QC columns/SL definition are deferred until measurements, not pending approval.
- RP-12/13: SAM 2 seeded propagation is the intended default; detector + BoT-SORT is comparison/fallback; pilot detection uses Grounding DINO / OWLv2. These are accepted design choices; actual model adapters and benchmarks remain work.
- RP-14/15/17: accept descriptive continuity metrics, TransNetV2 + CLIP shot stack and BORIS charts. Existing deterministic oracle/blob/adaptive-cut references remain available.
- RP-18 seed pixel/box provenance columns are approved for the next schema task. Retain SHOT_GAP saddle_no=0 and human chart schema/producer versions without CV provenance columns.
- Operator heading references config keys. Pilot kill-gate cutoffs now come from the selected registry. Isolated promotion test uses UTF-8 on Windows. Lint explicitly permits existing compact reference-code style, mathematical names and tool import bootstrapping; lambda/trailing-semicolon violations fixed.

Spec changes are ledger L-46 through L-50 in tools/cut_draft.py. Regenerate the draft; never edit generated prose directly. Historical proposal wording is superseded by the decisions above.

## Next tasks — execute now in this order

1. C6: make od1x-rehearsal. Chain synthetic clip, scriptable timer example, clean sheet templates and filled fixture proposals in a temporary directory. No new EG keys or invented evidence. One clean-checkout command must match existing instantiation fixtures.
2. C8: export_calibration_inputs.py. Export RaceGeometry sidecars and human charts from explicit frame JSON + store + manifest. Reject missing inputs, split/race mismatches and ambiguous producer selection. Test synthetic round-trip into the calibration harness; real calibration still refuses while DRAFT.
3. C3: environment fingerprint. Record actual versions, optional GPU/CUDA/torch, deterministic flags, seeds and weight hashes under versions.determinism_env. Missing values are null. Stable output on unchanged inputs; no guessed pins or claimed model execution.
4. C7: operator card, seeding walkthrough and start-type anchor prompts. Document only implemented keys; human-minutes must be real measurements.
5. RP-18 approved schema task: add seed_x_px, seed_y_px, seed_box_ref through DDL, writers, version metadata and canonical/coexistence tests together. Prompt pixels are provenance, not state-coordinate units.
6. D2: meaningful invariant tests for base partitions, overlay visibility, half-open intervals, unique lead, canonical ordering and marker binding. Then B4/B5 real adapters with synthetic references retained.

Update status/backlog/module READMEs and push this PR after each coherent block. Commit messages cite SPEC-2.0.0-draft and omit model identifiers. Do not overwrite concurrent work.

## Verification and actual blockers

Run lint, both spec lints, cut_draft.py --check, synthetic rehearsals and pytest. Run pytest last and unpiped before commit. On Windows set PYTHONUTF8=1; Make shell recipes assume POSIX, so use equivalent Python commands in PowerShell.

The draft has zero OPEN decisions and zero unbound EG markers. Freeze remains blocked by 19 uninstantiated evidence entries and KG-1 through KG-4. KG-5 remains the project go/no-go before P4. Replay paths/corpus, OD-1x observations and the pilot are still missing. Continue independent coding now; request real inputs when needed. Do not turn design decisions into synthetic evidence, real calibration, golden charting, M2 training or a claimed freeze.
