# Throwaway pilot stack build prompt (RP-2)

Spec: SPEC-2.0.0-draft; protocol: protocols/PILOT-5/PROTOCOL.md. This stack is exempt from G-1…G-3 and
its outputs are `producer_kind = pilot_throwaway`. Do not generalize it; it will be deleted.

Deliver, in this order, stopping when each works on one OD-1x replay:
1. `tools/seed_cli.py`: play/pause/step, click-runner→saddle number, `t`/`e` anchors, `q` writes
   `data/pilot5/<race_id>/seeds.json` + human-minutes. OpenCV window. ≥ 2× playback.
2. Detection + tracking: Ultralytics YOLO (COCO weights, class `horse`) + ByteTrack over the manually
   marked wide-pan intervals; expand boxes by a fixed factor toward the sulky; write per-frame boxes.
3. Pack-space projection: the simplest version of §3.1 (PCA axis, human-confirmed sign), centroid =
   center-bottom, SL = median box long side, SW = SL × sw_ratio. Call `tripstate.m4_geometry.cluster_tiers`.
4. Tier agreement script against `data/pilot5/<race_id>/tier_labels.csv` (owner-labelled) → KG-2 number.
5. Coverage + gates via `tripstate.m7_qc.evaluate_gates` → KG-3 per-stratum yield.
Write `data/pilot5/pilot_report.md` and fill `spec/registers/kill_gates.yaml`.
