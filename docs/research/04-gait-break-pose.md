# 04 — Gait, break-of-stride detection, pose (M6; v1.5 upgrade path)

## Question
Is there an off-the-shelf way to detect a trotter breaking into a gallop (« faute ») from broadcast video?

## Findings

- **No published video classifier for trot-vs-gallop in racing trotters was found.** Equine gait classification work is dominated by inertial sensors (e.g. transfer learning on raw IMU data from 326 horses: 91.9% multi-gait accuracy, 97.1% for a gallop-specific stage). ([ResearchGate IMU study](https://www.researchgate.net/publication/388621463_Automatic_gait_classification_for_equine_lameness_detection_using_transfer_learning), [TELUQ thesis](https://r-libre.teluq.ca/3750/1/MahautG%C3%A9rard2025.pdf))
- **Video work is keypoint-based and clinical** (side-view, walk/trot, lameness): DeepLabCut pipelines deriving stride length and stance time; a 2025 groundline study with 1–3% stride-detection failure from 2D keypoints; stride segmentation from pelvis vertical-position peaks. ([ASABE pipeline](https://elibrary.asabe.org/abstract.asp?aid=52547&t=5), [groundline study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12750506/), [gait events from upper body](https://www.researchgate.net/publication/346511480_Reliable_and_clinically_applicable_gait_event_classification_using_upper_body_motion_in_walking_and_trotting_horses))
- **Reference gait signatures exist:** foot-fall timings, duty factors and stride frequencies for walk, tölt, trot, pace, canters and gallops over a range of speeds (Robilliard et al., *J Exp Biol* 2007). These are the physical basis for any frequency/phase-based detector. ([JEB](https://journals.biologists.com/jeb/article/210/2/187/17107/Gait-characterisation-and-classification-in-horses))
- **Pretrained pose:** DeepLabCut **SuperAnimal-Quadruped** (HRNet-w32, 39 keypoints, trained on Quadruped-80K incl. Horse-30, Apache-2.0 on Hugging Face) is zero-shot for side-view quadrupeds; on Horse-10 OOD its normalised error is 0.109 vs 0.179 for ImageNet-initialised HRNet. Hoof-contact detection from keypoint traces by peak/valley detection is demonstrated in the same line of work. ([Model card](https://huggingface.co/mwmathis/DeepLabCutModelZoo-SuperAnimal-Quadruped), [Model Zoo](https://www.mackenziemathislab.org/dlc-modelzoo), [paper](https://arxiv.org/pdf/2203.07436)) *(leaderboard numbers unverified)*
- **3D horse pose/shape from video+audio** (CLHOP 2024) exists but is research-grade. ([arXiv 2407.01244](https://arxiv.org/pdf/2407.01244))

## Implications for the spec

1. **M6 v1 stands as written:** longitudinal-rank velocity anomaly + bbox vertical-oscillation regime change. The physics supports it: trot is a symmetric two-beat gait with a characteristic vertical oscillation frequency; a gallop changes both the frequency signature and the forward speed profile (the horse loses ground). Nothing better is available without labelled data, and the golden set must contain ≥ 20 dev / ≥ 10 held-out observable breaks regardless (§6.1).
2. **RP-16 (proposed register entry, v1.5):** pose-based gait classification using SuperAnimal-Quadruped keypoints on the tracked `horse_sulky` crops; stride frequency and limb-phase features; trained on the accumulated accepted/rejected `BREAK` candidates (the review loop is the labeller). Blocked on crop resolution in wide pans; likely viable only on tight shots, which are out of v1 scope.
3. **DR-09 split confirmed useful:** amble/pace (« traquenard ») is a different symmetric gait with its own signature; the `dai_gait_other` tag keeps those out of break calibration.
4. **Threshold namespace `m6_events`:** `osc_window_s`, `osc_freq_band_hz`, `osc_change_z`, `rank_vel_window_s`, `rank_vel_z`, `candidate_merge_s`.
