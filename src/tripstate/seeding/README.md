# seeding — operator loop core (M3 tool DoD)

`SeedingSession` holds the whole operator loop as a state machine with an injectable clock: keymap, playback with
auto-slowdown and pause at unresolved flags (DR-12), click → saddle number, orientation confirm/flip, `t_0`/`t_end`
capture with the EC-04 prompt, recall flag (EC-14), break-candidate accept/reject, first-past confirmation, human-minutes
and over-budget (Q-7), initial seeding seconds (KG-1). `tools/seed_cli.py` renders it in an OpenCV window and also replays
JSON action scripts headlessly (`--script`), which is how it is exercised without a display.

**Live loop (`live.py`):** `SeedingSession.attach(engine, monitor)` drives a `LiveEngine` frame by frame as the playhead moves (`OracleLiveEngine`, `DetectorLiveEngine` = detector + IoU tracker with click-bound tracklets, `SAM2LiveEngine` = chunked forward propagation, lazy import). `FlagMonitor` raises `lost`, `low_conf`, `overlap` and `reseed_needed` once per condition; a flag at or behind the playhead pauses playback immediately, one ahead triggers the DR-12 slowdown. A click + number on a flagged runner becomes a new prompt and resets observation from that frame. The session file carries the live `timeline`, which `pilot_run.py --propagator session` consumes without re-propagating.
