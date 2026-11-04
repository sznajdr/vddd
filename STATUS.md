# STATUS — live board

_Last updated: 2026-11-04 (agent scaffold)._ Update this file whenever a phase gate moves.

## Phase

**P1 — cut SPEC-2.0.0-draft.** P0 (foundation) complete.

## Facts established

- Spec lineage: 1.0.0 → 1.1.0 → 1.2.0, all dated 2026-07-25, all FROZEN. 1.x line closed.
- Review (2026-07-25) and RECON (2026-07-26) exist and are reconciled; residual conflicts: none claimed by RECON, several gaps found afterwards (see `spec/RECON-2.0.0-patches.md`).
- No footage has been inspected. OD-1 / OD-1x: **not run** (as far as this repo knows).
- No replays are in hand; replay source and rights unverified.
- Notule corpus and NLP artifacts referenced by §11 live outside this repo (owner's machine).

## Open questions for the owner

1. Has OD-1x, or any replay pull, happened since July 2026?
2. Where do the replays and the notule corpus live? Paths or a mount are needed for `data/`.
3. Do LeTrot's "Tracking" pages (per-runner tracking data at Vincennes) expose anything usable? If per-runner positional data exists officially, large parts of the CV plan are replaceable. Decide before P4.
4. Replay rights: Equidia terms were not read to completion. Confirm personal-use replay access is acceptable for the intended use.

## Blockers

| Blocker | Blocks | Owner |
|---|---|---|
| OD-1x not run | P5 freeze, every EG value | owner |
| Replays not sourced | P2, P4 | owner |
| Signal gate not run | go/no-go on the whole project | owner |

## Done

- [x] P0 repo scaffold, EG + kill-gate registries, threshold set TS-0.0.0-provisional
- [x] M0 metadata normalization implemented + tested (incl. S-3 statuses, `plausible_km_rate_min_s = 65`)
- [x] M4 tier clustering with `max_tier_span_sw` largest-gap split + D-26 cover predicate, tested (14-runner spread fixture)
- [x] M5 base-state table incl. `lead_uncovered_outside`, tested
- [x] M7 gate logic Q-1…Q-7 with closed failure codes, tested
- [x] M8 canonical export with fixed-decimal quantization (D-32), tested
- [x] `freeze_check.py` (fails while EG markers remain — expected)
- [x] `instantiate_eg.py` verified on synthetic sheets (dry run)
- [x] M0 video normalization (ffmpeg CFR, hashes, idempotent) + synthetic-clip tests
- [x] M5 smoothing + segment emission + DETACHED overlay, synthetic-trajectory tests (M5 DoD)
- [x] M7 SHOT_GAP events + coverage fractions
- [x] §6.2 metrics (mask IoUs, headline, Wilson CI, break matching, edit score, F1@k) + §6.4 audit sampler with operating characteristic
- [x] Research pack `docs/research/` (10 notes + sources) and `docs/STACK-2.0.md`

## Research pack (2026-11-04)

`docs/research/00-INDEX.md` — 13 findings mapped to modules and decisions; proposals RP-12…RP-20 in the patch list; proposed §13 stack in `docs/STACK-2.0.md`. Access/rights questions (replays, official tracking) are out of scope by owner decision.

## Owner decisions pending (see `spec/RECON-2.0.0-patches.md`)

- RP-5 lateral scale: per-shot `sw_ratio` if OD-1x shows > 2× variation.
- RP-6 LeTrot tracking data: read the pages before P4.
- RP-11 D-26 table gap: tier-1 leader covered by an outside runner. Recommended: keep `LEADER`, record `covered = true`.
- RP-12 seeded SAM 2 propagation as the M3 default (biggest design consequence of the research).
- RP-14 / RP-15 / RP-17 stack and metric additions (low risk, recommended).
- RP-19 / RP-20 geometry aids (only if OD-1x step 4 shows the lateral problem).
