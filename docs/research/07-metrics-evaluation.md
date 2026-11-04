# 07 — Evaluation conventions (§6.2–6.4, M7)

## Question
Do the field's evaluation conventions suggest additions or corrections to the spec's metrics?

## Findings

- **Temporal action segmentation** reports three things: frame-wise accuracy (MoF), segmental edit score (normalised Levenshtein distance over segment-label sequences), and segmental F1@{10, 25, 50} (segments matched by temporal IoU at each threshold; unmatched predictions = FP, unmatched truths = FN). Rationale repeated across papers: frame accuracy is dominated by long segments and blind to over-segmentation; edit/F1 reveal fragmentation. Reference: Lea et al. 2017. ([examples: arXiv 2604.01859](https://arxiv.org/pdf/2604.01859), [arXiv 2510.07652](https://arxiv.org/pdf/2510.07652), [TricorNet](https://arxiv.org/pdf/1705.07818))
- **MOT:** HOTA (with DetA/AssA) and IDF1 are the headline numbers; on SportsMOT, basketball is hardest (60.8 HOTA). ([SportsMOT](https://arxiv.org/pdf/2304.05170))
- **Game-state reconstruction** uses GS-HOTA, i.e. tracking + identity + pitch position jointly. ([SoccerNet 2025](https://arxiv.org/pdf/2508.19182))
- **Jersey numbers** are scored at tracklet level, not frame level. ([single-stage JNR](https://lukaszgrad.github.io/jnr))

## Implications for the spec

1. **RP-14 (proposed, descriptive only):** add to §6.2 the segmental **edit score** and **F1@{10,25,50}** per runner over base-state sequences, reported next to Segment IoU. DoD floors stay on the two mask IoUs (D-27) and macro IoU; the new metrics diagnose over-segmentation, which Segment IoU cannot see (a flickering prediction with the right total duration scores well on IoU and badly on edit/F1). Implemented in `src/tripstate/evaluation/metrics.py`.
2. **Identity audit (§6.4) stays tracklet-aware** (L-33's "≥ 8 distinct tracklet intervals" rule) — this matches the field's move to tracklet-level scoring.
3. **HOTA/IDF1 for M3** are not DoD metrics in the spec (identity is human-corrected), but the pilot should report HOTA/IDF1 of the *pre-correction* tracker against the corrected result, because that number predicts operator re-seed load (G-2's "≤ 8 ID swaps per race"). Add to `protocols/PILOT-5` measurements.
4. **Wilson CI** for DoD-2 (D-31) is implemented in the same module.
