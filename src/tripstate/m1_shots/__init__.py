"""M1 — Shot segmenter: numpy cut detector, blob shot-type classifier, static overlay detector, replay
cadence; TransNetV2 / CLIP adapters lazy. Acceptance evaluators included."""
from tripstate.m1_shots.segmenter import (
    SHOT_TYPES,
    BlobShotTypeClassifier,
    FrameDiffCutDetector,
    HistogramCutDetector,
    ShotRow,
    StaticOverlayDetector,
    boundary_f1,
    duplicate_fraction,
    segment,
    type_accuracy,
)

__all__ = ["SHOT_TYPES", "BlobShotTypeClassifier", "FrameDiffCutDetector", "HistogramCutDetector", "ShotRow", "StaticOverlayDetector",
           "boundary_f1", "duplicate_fraction", "segment", "type_accuracy"]
