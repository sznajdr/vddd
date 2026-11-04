# OD-1x — timed dry run on three replays (one afternoon)

**Supersedes OD-1.** Core = timed seeding; shot survey is the side effect. Instantiates the EG registry (`spec/registers/evidence_gated.yaml`) and feeds kill-gates KG-1 and KG-4.

## Before you start

- Three replays, one per D-22 stratum: **one autostart, one flat volte, one handicap volte**. Prefer a 14-runner field for at least one. Cover both pistes (GP / PP) if the betting corpus does (DR-06).
- Each replay's metadata record (official elapsed or RK per runner, `distance_run_m`, start format, piste, finish order, DAI list). Put raw metadata in `data/raw/<race_id>/metadata.json`.
- A stopwatch (`python tools/od1x_timer.py` works, or a phone), a video player with frame stepping and a timecode display, and the six sheets in `sheets/` copied to `data/od1x/`.
- Tooling is optional. The protocol is doable with a player, a notebook and the CSV templates.

Write `race_id`, `start_format`, `piste`, field size, day/night, and replay source/resolution/fps in `sheet_race.csv` first.

## Step 1 — Timed seeding (B-1, D-01, D-09, KG-1)

Per race:
1. Scrub to the **first stable wide-pan frame after the start** (whole field in frame, camera settled). Note the video timecode.
2. Start the stopwatch. Assign every saddle number to every runner you can see, writing them down in lane order. You may pause and step frames. Do not scrub forward more than 10 s.
3. Stop when all runners are assigned or you give up on one. Record: seconds elapsed, number assigned, number unassigned, how you identified them (number cloth / silks / driver / position), and how many you later found to be wrong when checking against the finish order.
4. Repeat once at a second wide-pan frame mid-race (simulates a re-seed after a cut).

Record in `sheet_seeding.csv`. The kill-gate reads the **median across the three races of the first-frame time**.

## Step 2 — Anchor reproducibility and bias (§1.3, D-34, EC-12, KG-4)

Per race, **three independent passes** (close and reopen the player between passes, or do the three races in rotation):
1. Click `t_0`: volte = the final release into racing direction; autostart = gate-car pull-away. If a recall/faux départ occurs, anchor the **final** release and tick `recall_suspected` (EC-14).
2. Click `t_end`: the first runner past the post, whatever the official result says (D-23).
3. Record both timecodes to the frame.

Afterwards, for each pass: `video_duration = t_end − t_0`; `residual = video_duration − official_elapsed_norm_s` of the first-past runner (use that runner's own `distance_run_m` to derive elapsed from RK if only RK is published, D-24). Record in `sheet_anchors.csv`. The instantiation rule uses the median residual per start type as the offset and ≈ p95 of |residual − offset| as the tolerance.

## Step 3 — Coverage (Q-1, Q-2, B-3)

Per race, from `t_0` to `t_end`, log every shot change with its timecode and type ∈ {wide_pan, head_on, tight, replay_insert, graphic_fullscreen, other}. Also note intervals where a full-screen or lower-third graphic covers runners.

Compute: % wide-pan over `[t_0, t_end]`; % wide-pan over the final third; number of replay inserts; number of cuts. Record in `sheet_coverage.csv`. This doubles as the M1 shot-boundary fixture for the OD-1x races.

## Step 4 — Geometry eyeball, including lateral scale (F-1, F-3, S-4, RP-5, RP-8)

Pick three wide-pan frames per race: **near straight**, **far straight**, **a bend**. In each frame, with a ruler on the screen or a screenshot:
1. Measure the median bbox long side of the sulkies (that is 1 SL) in pixels.
2. Measure the on-screen lateral separation between two runners you know are in adjacent lanes (one directly outside the other). Divide by SL. Record as `lane_gap_in_sl`.
3. Measure the lateral separation of a runner sitting "off the wheel" in a real cover position behind a runner in the next lane. Record as `cover_lat_in_sl`.
4. Note which side of the screen the rail is on (RP-8).
5. Note whether any longitudinal gap ≥ 6 SL exists anywhere in the frame (F-3 prevalence).

Record in `sheet_geometry.csv`. `tools/instantiate_eg.py` converts SL to SW using the configured `sw_ratio` and computes the per-location ratio for `sw_ratio_location_variation`. If `lane_gap_in_sl / sw_ratio` is below `same_tier_sw` anywhere, the tiering key set needs recalibration before any M4 work (RP-5).

## Step 5 — Finish-shot evidence (B-4, D-30)

Per race: in the finish shot(s), count how many runners you can see **crossing the line** with identifiable saddle numbers, and whether their order is unambiguous. Record in `sheet_finish.csv`. Instantiates `finish_evidence_min_k`.

## Step 6 — Recall / faux-départ scan (DR-03, EC-14)

Note any aborted start, what it looked like (deceleration, turn-back, restart footage, commentary cue), and whether the broadcast showed the restart. Record in `sheet_recall.csv`. Even "none observed" is a row.

## After the afternoon

```bash
python tools/instantiate_eg.py data/od1x --ts config/thresholds/TS-0.0.0-provisional.yaml --out spec/registers/evidence_gated.yaml --dry-run
```

Review the proposed values, then run without `--dry-run`. Commit the sheets and the registry together. Update `STATUS.md`.
