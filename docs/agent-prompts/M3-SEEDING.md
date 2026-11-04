# M3 seeding + tracking build prompt (RP-12 design; pilot first)

Spec: SPEC-2.0.0-draft §4 M3, §5.1, EC-08/09/12/14; ledger L-21…L-24; decisions D-01, D-02, D-16, D-30, D-34.
Research: docs/research/02-tracking-and-seeding.md.

Build, in order, each step testable on one OD-1x replay:
1. **Prompt store.** `id_assignments` gains `seed_x_px`, `seed_y_px`, `seed_box_ref` (RP-18). A seed = (shot_id, frame, saddle_no, x, y).
2. **Propagation.** For each wide-pan shot, run SAM 2 video propagation with one object per seeded saddle number. Output per frame per object: mask → bbox (`horse_sulky`), mask confidence. Store boxes in the tracklet sidecar with `method = human_seed` on the seed frame and `propagation` elsewhere.
3. **Flags, not fixes.** Raise an operator flag when mask confidence < `m3_track.mask_conf_flag`, when two masks overlap IoU > `m3_track.mask_overlap_flag` for > `m3_track.overlap_flag_s`, or when a mask vanishes for > `occl_max_s` (then emit NOT_VISIBLE, EC-08). The tool pauses at flags (≥ 2× auto-play otherwise, DR-12). Never re-associate automatically after a loss; a re-seed is a new prompt by the operator (`human_correction`).
4. **Cuts.** A new wide-pan shot starts with no objects; the tool proposes carrying the previous masks only when the camera-motion heuristic says the framing is continuous, and asks for confirmation; otherwise it asks for re-seeds of all runners (counts toward human-minutes).
5. **Comparison path.** Same clicks assigned post-hoc to BoT-SORT (GMC on) tracklets from the pilot detector. Report HOTA/IDF1 of both pre-correction tracks against the operator-corrected result, and the number of flags per race.
6. **Checks.** Wire `tripstate.m3_track.checks.anchor_check` (EC-12 with D-34 keys); finish/start checks per the stub contracts; `official_assumed` only with ≥ `finish_evidence_min_k` observed crossings (D-30).
Throughput target to report: frames/s with 14 objects on owner hardware (risk R-15).
