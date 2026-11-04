# Architecture

## Module graph (§4.0) and what exists today

```
replay + metadata
      │
      ▼
 M0 ingest ──────────── metadata rules + ffmpeg video normalization IMPLEMENTED
      │
      ▼
 M1 shots ───────────── stub (needs OD-1x shot labels)            ─┐
      │                                                             │ G-1
      ▼                                                             │
 M2 detect ──────────── stub (needs golden manifest for holdout)   ─┘
      │
      ▼
 M3 track + seeding ─── EC-12 arithmetic IMPLEMENTED · checks/tool stubs   ─┐ G-2
      │                                                                     │
      ▼                                                                     │
 M4 geometry ────────── tiering + cover IMPLEMENTED · projection stub      ─┘
      │                                                                     ┐ G-3
      ▼                                                                     │
 M5 states ──────────── classification + smoothing + segments IMPLEMENTED  ─┘
      │
      ▼
 M6 events ──────────── positions_lost IMPLEMENTED · detector stub
      │
      ▼
 M7 QC ──────────────── gates + yield + SHOT_GAP + coverage IMPLEMENTED · runner_qc stub
      │
      ▼
 M8 storage ─────────── canonical export IMPLEMENTED · DDL drafted · store stub
 evaluation ─────────── §6.2 metrics + §6.4 audit sampler IMPLEMENTED (tripstate.evaluation)
```

"IMPLEMENTED" means a pure-function reference implementation of a structurally frozen rule, reading every number from a threshold set. None of it is calibrated. None of it has seen a frame of video.

## Two stacks, one schema

| | Production stack (M0→M8) | Throwaway pilot stack (`protocols/PILOT-5`) |
|---|---|---|
| Purpose | the corpus | freeze evidence (KG-2, KG-3, budget distribution) |
| Gates | G-1…G-4 apply | exempt (RP-2) |
| Outputs | `producer_kind ∈ {cv_extract, human_chart, text_parse}` | `producer_kind = pilot_throwaway`, quarantined after freeze |
| Shares | schema (§9), threshold set, `tripstate.m4_geometry`, `tripstate.m7_qc` | |

## Data flow for one race (production)

1. `M0` writes `races`, `runners`, normalized video, hashes.
2. `M1` writes `shots`; wide-pan intervals gate everything downstream.
3. `M2` writes detections per wide-pan frame (sidecar).
4. Operator loop (`M3`, ≤ budget): orientation confirm → `t_0`/`t_end` → seed → tool auto-plays at ≥ 2× → re-seeds on flags → break review. Writes `id_assignments`, `race_anchors`, `shot_calibrations`, human-minutes.
5. `M4` projects to pack-space per frame; `M5` classifies + smooths into `state_segments`; `M6` proposes `BREAK` candidates → review → `BREAKING` overlays.
6. `M7` computes coverage, runs Q-1…Q-7, writes `qc`, `runner_qc`, `SHOT_GAP`.
7. `M8` persists; canonical JSONL + SHA-256 for DoD-5; default views join `chartable = true`.

## Determinism boundary (D-32)

Full-precision floats everywhere inside the pipeline. Quantization happens once, in `m8_storage.canonical`, for the hashable export. GPU nondeterminism is tolerated at the detection layer and absorbed by quantization; environment knobs are recorded under `producer_version`.
