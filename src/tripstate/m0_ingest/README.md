# M0 — Ingest & Normalization

**Spec:** SPEC-2.0.0-draft §4 M0 (+ L-18…L-20). **Status:** metadata normalization and ffmpeg video normalization (CFR via the `fps` filter, no interpolation, ffprobe sidecars, hashes, idempotent re-ingest, corrupt-file handling) implemented and tested on a synthetic clip; the 3-replay acceptance run waits for OD-1x footage.

| | |
|---|---|
| Input | Raw replay; race metadata record (`race_id`, date, meeting, race no., `base_distance_m`, `start_type`, `start_format`, `piste`, runners with `saddle_no`, `distance_run_m`, `autostart_row`, official times with raw strings, finish order, NP/DAI/DQ, revision evidence). |
| Output | Normalized CFR video + ffprobe metadata + hashes; `races` + `runners` rows per rules 1–6. |
| Acceptance | 3 sample replays normalized, duration within 1 frame, hashes stable. Metadata unit tests: 2100 autostart; 2850 flat volte; 2850/2875/2900 handicap with winner at 2900; elapsed duplicating km rate; disagreeing fields; malformed (`242` / `120`); winner with no time. **All implemented in `tests/test_m0_metadata.py`.** |
| DoD | Idempotent re-ingest; corrupt files → `ingest_failed`; ffmpeg provenance under `producer_version`. |

Build-prompt pointer: `docs/agent-prompts/M0.md`.
