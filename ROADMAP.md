# ROADMAP — phases, gates, exit criteria

Phases are sequential. A phase's exit gate is the only thing that opens the next.
Owner-hour estimates are rough and informative only.

| Phase | Name | Exit gate | Est. owner-hours |
|---|---|---|---|
| P0 | Foundation (this repo) | Repo scaffolded; EG registry + kill-gates machine-readable; evidence-independent logic unit-tested. | done (agent) |
| P1 | Cut SPEC-2.0.0-draft | **Done (agent, 2026-11-04):** 63 ledger edits applied by `tools/cut_draft.py`; 24 `[EG]` markers; `lint-spec` and `cut_draft.py --check` in CI. Owner review of the draft remains. | 3–5 (review) |
| P2 | OD-1x — one afternoon on footage | Six protocol steps recorded for 3 replays (autostart / flat volte / handicap volte); sheets in `data/od1x/`; `instantiate_eg.py` produces a filled registry. | 4–6 |
| P3 | Signal gate (parallel with P2) | Notule trip phrases from prior races tested against closing odds; a written go/no-go on whether trip data plausibly adds edge. | 6–10 |
| P4 | 5-race throwaway pilot | Pilot stack (exempt from G-1…G-3) runs end-to-end on 5 races; kill-gates evaluated; yield per stratum reported. | 10–20 |
| P5 | Freeze 2.0.0 | EG registry instantiated, kill-gates pass, `freeze_check.py` green, D-26…D-36 appended, one commit promotes DRAFT → FROZEN. **Tooling ready:** `tools/promote_draft.py` (rehearsed by `make freeze-dry-run`); `[OPEN]` markers and `stratum_yield_review_factor` must be resolved first. | 2 |
| P6 | Build M0→M8 + golden charting (OD-3) | Per-module acceptance tests pass in order with gates G-1…G-4; 30/10 golden set charted; calibration (`tools/calibrate.py`, §7.2) then DoD-1…6 evaluated at a declared freeze (`tools/evaluate_release.py`). | 60–90 |

Total to a ~600-race chartable corpus: roughly 90–120 owner-hours plus agent build time.

## What may start before the freeze (D-36 DRAFT rule)

- M0 ingest and metadata normalization (evidence-independent, already implemented in `src/tripstate/m0_ingest/`).
- Schema DDL and migrations (`src/tripstate/schema/`).
- Tooling scaffolds: seeding-tool skeleton, OD-1x helpers, freeze check.
- Pure-function reference implementations of structurally frozen rules (tiering, cover, state table, QC gates, canonical export) — numeric values read from a threshold set, never hard-coded.

## What MUST NOT start before the freeze

- Golden charting (OD-3). A hand chart made against a definition that then changes is wasted owner time.
- Calibration (§7).
- Any M2 training on owner annotations (the detector holdout rules depend on the golden manifest).

## Pilot exemption (resolves the pilot deadlock)

The kill-gates need M4 tier agreement and `chartable` yield from a 5-race pilot, but
G-1…G-3 block M4 until M1–M3 pass acceptance on golden data that cannot exist before
the freeze. Resolution: the pilot runs on a **throwaway stack** under
`protocols/PILOT-5/`. Its outputs are evidence for the freeze only, never corpus
artifacts, and carry `producer_kind = pilot_throwaway`. Gates G-1…G-3 do not apply
to it. This exemption is written into the draft §0.4 (see `RECON-2.0.0-patches.md`, RP-2).
