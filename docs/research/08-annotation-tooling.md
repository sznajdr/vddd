# 08 — Annotation and charting tooling (OD-3, §5.2, M2/M4 fixtures)

## Findings

- **CVAT** (open-source, self-hosted community edition): video annotation with interpolation and timeline, SAM 2 pre-annotation; generally rated the stronger video tool. **Label Studio**: multimodal generalist, SAM 2 video tracking via an ML backend that (as of its Aug 2024 tutorial) tracked one object at a time and required a GPU server. Other open-source: LightlyStudio, FiftyOne (visualisation/evaluation), VGG Image Annotator. ([Roboflow comparison](https://roboflow.com/compare-labeling-tools/cvat-vs-label-studio), [Label Studio SAM2 tutorial](https://labelstud.io/tutorials/segment_anything_2_video), [Lightly 2026 guide](https://lightly.ai/blog/8-best-cvat-alternatives-for-computer-vision-teams-in-2026))
- **BORIS** (Friard & Gamba, *Methods Ecol Evol* 2016; GNU/Linux, Windows, macOS): free, open-source event logging over video with a user-defined ethogram of **state events** (start/stop keys, unpaired-event warnings) and **point events**, modifiers to reduce key count, no limit on subjects/events, exports TSV/CSV/JSON/SQL. ([user guide](https://www.boris.unito.it/user_guide/coding/), [paper record](https://iris.unito.it/handle/2318/1589424))

## Implications for the spec

1. **RP-17 (proposed): hand-charting runs in BORIS.** Ethogram = the §2.3 base states as state events, `DETACHED` as a state event with a `front|rear` modifier, `BREAK` as a point event (start) plus a state event (`BREAKING`), `SHOT_GAP` as a state event on a pseudo-subject "camera"; subjects = saddle numbers. One key per state, one subject selector. Export → a converter (`tools/boris_to_hand_charts.py`, to build) writes `hand_charts` rows with `t_*_frac` computed from the charter's own `t_0`/`t_end` point events. This removes the need to build any charting UI and gives the §5.2 "charter's choice" of segment notation for free.
2. **Frame fixtures (M2 boxes, M4 tier/order labels)** go in CVAT with SAM 2 pre-annotation; export to repo-owned formats (COCO JSON for boxes; CSV for per-runner tier/order labels) so the platform is not a dependency (§13 already says so).
3. **OD-1x needs none of this.** A player with frame stepping, a stopwatch and the CSV sheets suffice.
