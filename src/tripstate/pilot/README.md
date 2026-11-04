# pilot — throwaway pilot stack (protocols/PILOT-5; RP-2)

| Piece | Runs here (synthetic) | Real-replay adapter (lazy import) |
|---|---|---|
| Frames | `FrameSource` (ffmpeg rawvideo pipe), `render_synth_video` | same |
| Detector | `OracleDetector` (truth + jitter/dropout), `BlobDetector` (pure-numpy components) | `GroundingDinoDetector`, `OWLv2Detector` (transformers), `UltralyticsDetector` (COCO horse, AGPL) |
| Tracker | `IoUTracker` (ByteTrack-style two-stage IoU, constant velocity, `m3_track` thresholds) | Ultralytics trackers can be substituted at the same interface |
| Seeded propagation | `OraclePropagator` (prompt inside a truth box binds the id; loss windows) | `SAM2Propagator` (sam2 video predictor; obj_id = saddle number) |
| Identity | `assign_seeds_to_tracks` (click → tracklet, never re-association), flags `seed_missed`, `id_conflict`, `lost`, `reseed_needed`; seeded path flags `low_conf`, `lost`, `overlap` | same |
| Metrics | `trackeval`: IDF1, ID switches, MOTA-lite (local Hungarian) | same |
| Race run | `run_pilot_race` → M4 → M5 → coverage → EC-12 → gates → `PilotRaceReport` (`producer_kind = pilot_throwaway`) | same |
| Report | `report.aggregate` → KG-1…KG-4 → `write_kill_gates` + markdown | same |

Nothing here enters the corpus. Model adapters are written against the published APIs but are untested in this repository (no GPU, no weights); mark them verified in the pilot log the first time they run.
