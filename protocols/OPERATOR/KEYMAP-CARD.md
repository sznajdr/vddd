# Seeding tool — operator card (one page)

`python tools/seed_cli.py VIDEO --race <race_id> --start-type <autostart|volte> --start-format <autostart|volte_flat|volte_handicap> --out data/pilot5/<race_id>/`
(add `--engine sam2 --sam2-ckpt …` or `--engine detector --detector gdino|owlv2|yolo` for live propagation and flags).
Every key below exists in `tripstate.seeding.session.KEYMAP`; nothing else does anything. Human-minutes run from your first click or key to `q` (DoD-3, Q-7) — they are measured, never typed in.

## Keys

| Key | Action | When |
|---|---|---|
| `space` | play / pause | any time |
| `,` / `.` | step one frame back / forward | paused |
| `[` / `]` | jump to the previous / next unresolved flag | any time |
| `1` `2` `4` `8` | playback speed ×1 ×2 ×4 ×8 (auto-slowdown to ×1 near an unresolved flag, pause on it — DR-12) | playing |
| `o` | confirm the proposed orientation (travel direction + rail side) for the current shot | at the start of each wide-pan shot; always when the proposal is low-confidence or changed |
| `O` / `R` | flip the travel direction / flip the rail side (human correction) | when the proposal is wrong |
| click | select the runner under the pointer, then type its saddle number and `Enter` | initial seed on the first stable wide-pan frame; re-seed on a flagged runner |
| `t` / `e` | capture `t_0` / `t_end` on the current frame (D-10; see ANCHOR-PROMPTS.md for what each means per start type) | once each; re-click only when the tool asks (EC-12) |
| `r` | raise / clear the "possible recall" flag (EC-14) | aborted start seen |
| `a` / `x` | accept / reject the break candidate at the playhead (M6 review loop) | when the HUD shows a pending candidate |
| `f` | confirm the first-past runner: type its saddle number and `Enter` (M3 DoD (a), D-23) | at the finish, when asked |
| `Escape` | cancel a pending number entry | while typing a number |
| `Enter` | finish the number you typed | after click or `f` |
| `q` | finish: writes seeds, anchors, decisions and human-minutes to `session.json` | last action of the race |

## Rules of thumb

- Over the budget cap (`human_budget_cap_min`, HUD shows **OVER BUDGET**): finish for diagnosis if you like, the race is `over_budget` and excluded (D-09, Q-7). Do not rescue it.
- A flag is a question, not a correction: the tool never re-associates on its own (EC-08/09). Resolve it with a click + number, or move on.
- `o` first, then `t`, then seeds. Orientation unconfirmed = the shot's geometry has confidence 0 (§3.1).
- Scripted replays (`--script`) are headless: their wall-clock is **not** human-minutes and the pilot runner ignores it.
