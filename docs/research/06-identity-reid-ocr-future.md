# 06 — Automatic identity: saddle-cloth OCR, silks, re-ID (banned in v1; register ≥ v2)

## Question
What would fully automatic identity look like when the seeding clicks have accumulated into a training set?

## Findings

- **Jersey number recognition (soccer):** single-stage uncertainty-aware recognition reaches 85.6% tracklet-level accuracy on the SoccerNet benchmark (CVPR 2025 workshop), up from 35.8% (2015) and 49.9% (2021). SoccerNet 2024/2025 entries fine-tune YOLO-family digit detectors or use PARSeq OCR on torso crops selected via pose keypoints; VLMs were also used by strong entries. Keyframe selection matters at low resolution. ([single-stage JNR](https://lukaszgrad.github.io/jnr), [SoccerNet 2025](https://arxiv.org/pdf/2508.19182), [SoccerNet 2024](https://arxiv.org/pdf/2409.10587), [keyframe JNR](https://arxiv.org/pdf/2309.06285))
- **Horse racing:** a patent (US 2021/0264159) combines silk/cap detection with embeddings (enrol new silks without retraining) and uses saddle-number OCR only as a secondary cue because it is rarely visible. Surrey's CVMP 2024 work argues helmets are the robust cue. "Horse ReIDing" (ISACE 2025) builds a jockey re-ID pipeline on ResNeXt; an independent GitHub project (21 identities, 3 clips) found Grad-CAM attention on silks and helmets, not the horse. ([patent](https://patents.justia.com/patent/20210264159), [Surrey](https://openresearch.surrey.ac.uk/esploro/outputs/conferenceProceeding/Detection-and-Re-Identification-in-the-case/99925861902346), [Springer](https://link.springer.com/chapter/10.1007/978-3-032-06167-6_16), [GitHub](https://github.com/Saunak2703/DEEP-LEARNING-BASED-HORSE-REID))
- **Generic player re-ID:** CLIP-ReIdent (contrastive) is a reference for appearance embeddings in sports. ([arXiv 2303.11855](https://arxiv.org/pdf/2303.11855))

## Implications for the spec

1. **The v1 ban (D-01) is consistent with the evidence:** at broadcast resolution the number is rarely legible; the published horse-racing systems lean on silks/caps, which in French trot are the **driver's** colours and change with the driver, so an enrolment database would be per driver-colours, not per horse.
2. **What to collect now so v2 is cheap:** every seeding click already stores `seed_frame`/`seed_video_s`; adding the click pixel coordinates and the mask/box at seed time (schema-additive, L-38-style) turns the whole corpus into a labelled re-ID + OCR dataset at zero extra operator cost. Proposed columns on `id_assignments`: `seed_x_px`, `seed_y_px`, `seed_box` (sidecar ref).
3. **Register entry refinement (§12):** "Fully automatic identity (≥ v2)" → split into (a) silks/cap embedding re-ID as a *flag source* (could enter v1.5 as an `id_suspect` heuristic, no identity assignment), (b) saddle-cloth OCR on tight shots only (v2+), (c) full assignment (v2+). Owner decision.
