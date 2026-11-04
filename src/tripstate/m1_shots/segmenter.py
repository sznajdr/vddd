"""M1 shot segmenter — STUB (SPEC-2.0.0-draft §4 M1; EC-06, EC-07).

Contract: `shots` rows (shot_id, type in {wide_pan, head_on, tight, replay_insert,
graphic_fullscreen, other}, t_start_video_s, t_end_video_s, confidence, graphic_overlay_mask_ref);
contiguous, non-overlapping, full coverage. Acceptance on OD-1x labels: boundary F1 >= 0.90
(±0.5 s), wide-pan accuracy >= 0.95, leave-one-race-out for learned parts, overlay mask F1 >= 0.90.
Low-confidence -> `other` (not charted). replay_insert MUST be separated (corpus poisoning).
Default stack: PySceneDetect + small frame classifier + static overlay-mask detector.
Thresholds: namespace `m1_shots` in the TS YAML (must exist before acceptance).
"""


def segment_shots(normalized_video_path, ts):
    raise NotImplementedError("M1: SPEC-2.0.0-draft §4 M1; needs OD-1x shot-labelled replays")
