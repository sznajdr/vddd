"""M2 detector — STUB (SPEC-2.0.0-draft §4 M2; EC-05).

Contract: per wide-pan frame, `horse_sulky` bboxes + confidence (single class). Acceptance on the
race-disjoint detector holdout (>= 500 frames, >= 5 races, day + night): AP@0.5 >= 0.90, per-frame
recall >= 0.95 in fields <= 14. DoD: both strata; >= 4x real-time soft target.
Determinism (D-32): record use_deterministic_algorithms, cudnn.benchmark, TF32, driver and weight
hashes under producer_version; bit-exact across machines is NOT required (canonical export is quantized).
Pilot (RP-2): off-the-shelf COCO `horse` with sulky-expanded boxes is acceptable for the throwaway run only.
"""


def detect_frames(frames, ts):
    raise NotImplementedError("M2: SPEC-2.0.0-draft §4 M2; blocked on G-1 and the golden manifest")
