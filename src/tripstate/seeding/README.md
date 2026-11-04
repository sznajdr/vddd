# seeding — operator loop core (M3 tool DoD)

`SeedingSession` holds the whole operator loop as a state machine with an injectable clock: keymap, playback with
auto-slowdown and pause at unresolved flags (DR-12), click → saddle number, orientation confirm/flip, `t_0`/`t_end`
capture with the EC-04 prompt, recall flag (EC-14), break-candidate accept/reject, first-past confirmation, human-minutes
and over-budget (Q-7), initial seeding seconds (KG-1). `tools/seed_cli.py` renders it in an OpenCV window and also replays
JSON action scripts headlessly (`--script`), which is how it is exercised without a display.

Not yet wired: live propagation/flag generation inside the window (the window shows precomputed tracks/flags). The pilot
runs seeding and propagation as two passes: seed → propagate → flags → re-seed pass.
