# Research pack — state of the art and resources that fit this project

**Date:** 2026-11-04. **Scope:** technical only (detection, tracking, seeding, shot segmentation, gait/break detection, geometry, identity, metrics, tooling, determinism, domain literature). Data access, replay rights and official tracking feeds are out of scope by owner decision (they sit behind accounts or paywalls).

**Method and caveats.** All findings come from web search summaries made from this session; `arxiv.org` and `docs.ultralytics.com` could not be fetched directly (blocked by the session's network policy), so paper-level numbers are quoted from secondary summaries and marked *(unverified)* where the primary text was not read. Before any number here enters the spec, read the primary source. `SOURCES.md` lists every URL used.

## Reading order

| File | Question it answers | Modules |
|---|---|---|
| `01-detection.md` | What detects a horse+sulky with zero training, and what to fine-tune later | M2, pilot |
| `02-tracking-and-seeding.md` | How to turn one click per horse into a race-long identity track | M3, D-01 |
| `03-shot-segmentation-graphics.md` | How to find wide-pan segments, replays and graphics overlays | M1 |
| `04-gait-break-pose.md` | What exists for break-of-stride detection from video | M6 |
| `05-geometry-camera.md` | Camera motion, calibration literature, and the lateral-scale risk | M4, D-07, RP-5 |
| `06-identity-reid-ocr-future.md` | What v2 automatic identity would look like | §12 register |
| `07-metrics-evaluation.md` | Which evaluation conventions the field uses, and what to add to §6.2 | M7, §6 |
| `08-annotation-tooling.md` | Tools for frame labels and for hand-charting | OD-3, §5.2 |
| `09-domain-trip-literature.md` | What is known about cover/parked effects and existing chart notations | §2, signal gate |
| `10-determinism.md` | What bit-reproducibility actually requires | D-32, M8 |

## Headline findings and what they change

| # | Finding | Confidence | Implication | Where applied |
|---|---|---|---|---|
| 1 | **Promptable video segmentation (SAM 2 family) is the natural implementation of D-01 seeding.** One click per runner on a wide-pan frame, mask propagated through the shot, re-prompt on failure. Meta's own annotation loop reports ~8× speed-up with SAM 2 in the loop. SAM2-based trackers (SAMURAI, DAM4SAM, SAM2MOT, SAMURAI++) add motion-aware memory for multi-object use. | High for the mechanism; medium for throughput at 14 objects | M3 default tracker should be "click-seeded mask propagation + Kalman/CMC", not detector+ByteTrack with post-hoc click assignment. Seeding clicks become prompts, not just labels. | RP-12; `02-tracking-and-seeding.md`; `docs/agent-prompts/M3-SEEDING.md` |
| 2 | **SAM 3 (Nov 2025) adds text-concept prompts ("horse pulling a sulky") with detection+tracking in one model; near real-time only for ~5 concurrent objects, 30 s clip prompts.** | Medium (vendor + reviews) | Candidate for the throwaway pilot's zero-training detector. Not production: object-count latency scaling vs 14 runners. | RP-13 |
| 3 | **Open-vocabulary detectors: Grounding DINO for accuracy, OWLv2 (Apache-2.0) as a simple baseline, YOLO-World for speed.** Objects365 has `Horse` and `Carriage` classes; no public dataset has a sulky class. | High | Pilot detector = Grounding DINO or OWLv2 with prompt "horse and sulky"; production M2 = fine-tuned YOLO/RF-DETR on owner boxes, pretrain from Objects365 weights if available. | `01-detection.md` |
| 4 | **The only published horse-racing MOT work (Ng et al., Information Sciences 2023) had 15 labelled videos and used GAN augmentation; no public dataset exists.** | High | The golden frame fixtures are not optional; nothing can be downloaded instead. Confirms §6.1 sizing. | `01-detection.md` |
| 5 | **Training-free sports MOT (McByte / McByte++ 2025–2026) combines mask propagation + camera-motion compensation + online re-ID, reporting top HOTA/IDF1 without training.** | Medium *(abstract only)* | Second candidate for M3 if SAM-based memory trackers are too slow at 14 objects. | `02-tracking-and-seeding.md` |
| 6 | **BoT-SORT's camera-motion compensation is the component designed for panning; OC-SORT is favoured for non-linear motion.** No controlled broadcast-panning benchmark found. | Medium | Pilot: BoT-SORT with GMC on; OC-SORT as the comparison. Add `gmc_method` to the `m3_track` namespace. | `05-geometry-camera.md` |
| 7 | **No video-based trot-vs-gallop classifier was found for racing trotters; equine gait work is IMU-based or keypoint-based side-view clinical work.** SuperAnimal-Quadruped (DeepLabCut, Apache-2.0) gives 39 keypoints zero-shot on side-view quadrupeds incl. horses. | High (absence) | M6's bbox-oscillation + rank-velocity signal stands as v1; pose-based gait classification is a v1.5 upgrade path with a named pretrained model. Breaks must be hand-labelled in the golden set (already required). | RP-16; `04-gait-break-pose.md` |
| 8 | **Shot boundary SOTA is TransNetV2 (F1 ≈ 0.94–0.96 on broadcast benchmarks); shot-type classification has no zero-shot benchmark but CLIP prompt-ensembles are the standard recipe; replay detection in soccer uses logo transitions; graphics overlays are found by temporal static-region analysis.** | High / medium | M1 = TransNetV2 cuts → CLIP zero-shot shot type with prompt ensemble → static-region overlay mask. SoccerNet-v2's 13-camera taxonomy is a reference for naming. | RP-15; `03-shot-segmentation-graphics.md` |
| 9 | **Sports field registration (TVCalib, PnLCalib) needs known field templates and markings; nothing works without markings.** | High | The homography ban (§3.3) is justified, not merely cautious. A trot track has rails but no template; rail lines could at most give a vanishing direction. | `05-geometry-camera.md` |
| 10 | **Action-segmentation evaluation uses frame accuracy + segmental edit score + F1@{10,25,50}.** | High | Add edit score and F1@k as *descriptive* metrics next to Segment IoU in §6.2; keep DoD floors on IoU. | RP-14; `07-metrics-evaluation.md` |
| 11 | **Commentary text alone rivals video for soccer event spotting (2025).** Drafting behind another horse measurably increases speed in Thoroughbreds (Spence et al. 2012, 3,357 races). | Medium / high | Supports the §11 text workstream and the signal gate: trip phrases may carry most of the usable signal before any CV. Cover is physically real, not just lexicon. | `09-domain-trip-literature.md` |
| 12 | **BORIS (open-source ethology coder) already does keyed state/point coding over video with CSV/JSON export.** | High | Hand-charting (§5.2) can run in BORIS with an ethogram = our state set; export maps to `hand_charts`. Saves building a charting UI. | RP-17; `08-annotation-tooling.md` |
| 13 | **Bit-exact reproducibility is only expected on the same GPU architecture, library versions and GPU count; TF32 and cuDNN autotune must be pinned.** | High | D-32's quantized canonical export is the right contract; record the knobs. | `10-determinism.md` |

## What this pack does not settle

- Throughput of SAM-based trackers with 14 simultaneous objects on owner hardware. Only a pilot measurement answers it.
- Whether a lateral-scale correction is needed (RP-5). Only OD-1x step 4 answers it.
- Whether trip phrases carry edge over the market. Only the signal gate answers it.
