# Proposed §13 default stack for 2.0.0 (NON-NORMATIVE, D-15) — informed by `docs/research/`

Two columns because the throwaway pilot (RP-2) and production have different goals: the pilot must run in days with zero training; production must pass §4 acceptance.

| Concern | Throwaway pilot (freeze evidence) | Production (post-freeze) | Research |
|---|---|---|---|
| Shot boundaries | TransNetV2 inference, no training | TransNetV2 + threshold under `m1_shots.cut_thresh`, calibrated on OD-1x labels | 03 |
| Shot type | CLIP zero-shot prompt ensemble, or manual intervals from the OD-1x coverage sheet | CLIP zero-shot ensemble → small linear probe on OD-1x labels (leave-one-race-out) | 03 |
| Graphics overlay | skip (Q-5 computed from manual notes) | temporal static-region mask + per-broadcaster priors | 03 |
| Detection | Grounding DINO / OWLv2 prompt "horse pulling a sulky" (SAM 3 if GPU allows) | fine-tuned single-class detector (RF-DETR or YOLO family), Objects365-initialised, race-disjoint holdout | 01 |
| Identity seeding + tracking | SAM 2 point-prompt propagation per runner (clicks = prompts); BoT-SORT+GMC on detections as comparison | same, with DAM4SAM/SAM2MOT-style memory management for 14 objects; McByte++ as alternative | 02 |
| Appearance re-ID | none | flag source only (D-01): online embedding to raise swap flags | 02, 06 |
| Pack geometry | `tripstate.m4_geometry` on mask-bbox centroids; PCA axis with human-confirmed sign | + rail-line direction prior for the axis; local-neighbourhood axis on bends (EG) | 05 |
| States | `tripstate.m5_states` (implemented) | same | — |
| Breaks | none (hand-noted) | bbox-oscillation + rank-velocity (M6 as specified); v1.5: SuperAnimal-Quadruped pose gait | 04 |
| QC / metrics | `tripstate.m7_qc`, `tripstate.evaluation` (implemented) | same + edit score / F1@k descriptive | 07 |
| Hand charting | — | BORIS ethogram → `tools/boris_to_hand_charts.py` | 08 |
| Frame labels | — | CVAT with SAM 2 pre-annotation; repo-owned exports | 08 |
| Determinism | record env knobs | `use_deterministic_algorithms`, benchmark off, TF32 off, pinned versions, quantised canonical export | 10 |
| Storage | JSON/CSV in `data/pilot5/` | SQLite + parquet per `schema/ddl.sql` | — |

Licences to check before production: SAM 2/3 (Meta licence terms), Grounding DINO (Apache-2.0), OWLv2 (Apache-2.0), YOLO-World/Ultralytics (AGPL-3.0 for Ultralytics packages), RF-DETR (Apache-2.0), SuperAnimal (Apache-2.0 model card), TransNetV2 (MIT), BORIS (GPL-3.0), CVAT (MIT).
