# Ten-minute seeding walkthrough (synthetic video, no replay needed)

Goal: do the whole operator loop once on the synthetic clip so the real races hold no surprises. Everything here runs today; nothing it produces is evidence (synthetic race, synthetic boxes).

## 1. Make the clip (1 min)

```bash
python tools/synth_video.py --out data/synth --duration 20
```
Writes `data/synth/synth.mp4` (7 scripted runners, a 0.6 s occlusion, a late rear detachment), the truth boxes, `seeds.json`, `tier_labels.csv`, `race.json` and a headless `seed_script.json`.

## 2. Watch the headless replay first (1 min)

```bash
python tools/seed_cli.py data/synth/synth.mp4 --race SYNTH-1 --out data/synth/session --script data/synth/seed_script.json --engine oracle --truth data/synth/synth.mp4.truth.json
```
The script presses `o`, `t`, clicks every runner and types its number, sets speed `8`, plays through, resolves flags, captures `e`, confirms the first-past runner with `f` and quits with `q`. Open `data/synth/session/session.json`: `seeds`, `anchors`, `flags`, `human_minutes` (from a headless run: ignored downstream, `headless: true`).

## 3. Do it yourself with the window (5 min)

Needs `opencv-python` and a display.

```bash
python tools/seed_cli.py data/synth/synth.mp4 --race SYNTH-1 --start-type autostart --out data/synth/session-manual --engine oracle --truth data/synth/synth.mp4.truth.json
```
1. The HUD shows the EC-04 line for the start type (`autostart: t_0 = gate-car pull-away`). Press `o` to confirm the orientation proposal (travel sign +1, rail right of travel in the synthetic clip).
2. Press `t` on the first frame (the synthetic race starts at frame 0).
3. Click each runner, type its number, `Enter`. Seven runners; `,`/`.` to step if two overlap.
4. Press `8`, then `space`. The tool slows to ×1 and pauses at the flag raised when runner 5 disappears (frames 100–115 at 25 fps). Press `]` to go to it, click runner 5 when it is back, type `5`, `Enter`.
5. Let it play to the end. Press `e` on the frame the first runner crosses (the synthetic finish is the last frame). Press `f`, type `1`, `Enter`.
6. Press `q`. Your real wall-clock is now in `session-manual/session.json` under `human_minutes` — that is the kind of number OD-1x step 1 and the pilot want, nothing else.

## 4. Run the pilot pipeline on your session (2 min)

```bash
python tools/pilot_run.py --video data/synth/synth.mp4 --race SYNTH-1 --race-json data/synth/race.json --session data/synth/session-manual/session.json \
  --truth data/synth/synth.mp4.truth.json --tier-labels data/synth/tier_labels.csv --path seeded --propagator session --out data/pilot5/SYNTH-1
python tools/pilot_report.py --reports 'data/pilot5/SYNTH-1/report_*.json' --md data/pilot5/pilot_report.md
```
`pilot_report.md` shows KG-1…KG-4 as the kill-gate aggregation would compute them. With a manual session the human-minutes column is real; with the scripted session it is omitted unless `--human-minutes` is passed explicitly (dry runs only).

## 5. What to carry to the real day

- The card (`KEYMAP-CARD.md`) next to the keyboard; `ANCHOR-PROMPTS.md` for the volte races.
- `tools/od1x_timer.py` for OD-1x step 1 (the seeding tool measures the full loop; the stopwatch measures the first-frame seeding alone).
- `make od1x-rehearsal` the evening before: it regenerates all of this in `/tmp` and checks the instantiation proposals against the committed fixture.
