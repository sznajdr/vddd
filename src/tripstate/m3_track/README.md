# M3 — Tracking + Seeding Tool
**Spec:** §4 M3, §5.1, EC-04/09/10/12/14; ledger L-21…L-24; D-23/25/30/34. **Status:** checks implemented and fixture-tested: EC-12 (D-34), crossing reconstruction from boxes and a finish line, the finish check with reference-order basis, the D-25/D-30 first-past ladder (relegation fixture and zero-crossing fixture pass), adjudication routing, autostart two-row and volte band start checks (DR-04). Live seeding loop in `tripstate.seeding`.

Tool DoD (D-16, DR-12): keyboard frame-stepper, click-runner → saddle number, jump-to-flagged-cut, orientation confirm, `t_0`/`t_end` capture, break confirm/reject, first-past confirm, **≥ 2× auto-play with slowdown at flagged events**, "possible recall" flag, human-minutes logged automatically.

Gate out: G-2 (ID-assigned tracklets on ≥ 3 dev golden races within budget). The throwaway pilot is exempt (RP-2).

`assignments.py` (RP-18, L-51): `id_assignments` rows from operator seeds — `rows_from_session` (seeded/SAM 2 path: tracklet = prompt object id, `seed_box_ref = mask:<id>@<frame>`) and `rows_from_pilot` (comparison path: the tracklet the click landed on, `track:<id>@<frame>`); `seed_x_px` / `seed_y_px` keep the click in source-frame pixels as identity provenance, never as a state coordinate. The pilot runner (`tripstate.pilot.run`) fills `PilotRaceReport.id_assignments` on both paths.
