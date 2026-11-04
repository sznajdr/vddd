# Anchor prompts per start type (EC-04, D-10, D-23, EC-12, EC-14)

The seeding tool shows one line (`SeedingSession.start_prompt()`) before anchor capture. This page says what the line means and what to click.

| Start type / format | HUD line | `t_0` = press `t` on … | `t_end` = press `e` on … |
|---|---|---|---|
| `autostart` | `autostart: t_0 = gate-car pull-away` | the first frame where the gate car pulls away from the field (not the moving start's approach) | the frame the **first runner's nose** crosses the finish line, whatever the stewards decide later (D-23) |
| `volte` / `volte_flat` | `volte (volte_flat): t_0 = FINAL release into racing direction; bands flat` | the frame of the **final** release into racing direction after the volte (the "départ lancé" moment) | same as above |
| `volte` / `volte_handicap` | `volte (volte_handicap): t_0 = FINAL release into racing direction; bands 2850 m: n runners, 2875 m: n runners, …` | the final release of the **front band**; back-markers are released from their own marks and start behind by construction (D-22 — never "correct" for it) | same as above |

## Recall / faux départ (EC-14)

If the start is aborted and restarted: anchor the **final** release, press `r` so `recall_suspected = true`, and note the first release's timecode in the sheet (`sheet_recall.csv` on OD-1x). The tool never moves `t_0` on its own.

## When the tool asks you to re-click (EC-12)

After both anchors, the tool compares `t_end − t_0` with the first-past runner's normalized official time using the per-start-type offset and tolerance (`anchor_offset_<start_type>_s`, `anchor_tol_<start_type>_s`, D-34). A mismatch prompts **one** re-click of the suspect anchor. If it persists, the race becomes `anchor_suspect` and unchartable (Q-3); do not hunt for a frame that makes the number fit. No official time → `inconclusive`, nothing to do.

## First past the post (`f`)

Type the saddle number of the runner that crossed first **as seen**. If the finish shot shows fewer than `finish_evidence_min_k` identifiable crossings and the first crossing was not observed, leave the adjudication to the tool's ladder (D-25/D-30): it will record `first_past_saddle_no = NULL` rather than assume the official winner.
