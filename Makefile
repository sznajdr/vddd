.PHONY: help setup check test lint lint-spec lint-docs freeze-check dry-runs freeze-dry-run calibrate-dry-run evaluate-dry-run od1x-rehearsal od1x-timer synth-demo pilot-demo cut-draft check-draft

help:               ## list targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' | sort

# ---- setup and checks -----------------------------------------------------------------------------------------------
setup:              ## pip install -e ".[dev]" (ffmpeg must be installed separately)
	pip install -e ".[dev]"

check: lint lint-spec lint-docs test   ## everything CI runs that must be green (pytest last, unpiped)

test:               ## unit, acceptance and property tests
	python -m pytest -q

lint:               ## ruff
	ruff check src tests tools

lint-spec:          ## spec table hygiene, decision refs, EG flags, draft reproducibility (+ the frozen file once it exists)
	python tools/lint_spec.py spec/SPEC-2.0.0-draft.md spec/registers/evidence_gated.yaml
	python tools/lint_spec.py spec/SPEC-2.0.0-draft-LEDGER.md spec/registers/evidence_gated.yaml
	python tools/cut_draft.py --check
	@if [ -f spec/SPEC-2.0.0.md ]; then python tools/lint_spec.py spec/SPEC-2.0.0.md spec/registers/evidence_gated.yaml; fi

lint-docs:          ## documentation hygiene: referenced paths exist, tools/packages indexed, make targets exist
	python tools/lint_docs.py

freeze-check:       ## D-36 gate; EXPECTED TO FAIL until OD-1x and the pilot instantiate the registry
	python tools/freeze_check.py

# ---- rehearsals (synthetic inputs, temp dirs, never evidence) --------------------------------------------------------
dry-runs: freeze-dry-run calibrate-dry-run evaluate-dry-run od1x-rehearsal   ## all four rehearsals

freeze-dry-run:     ## synthetic OD-1x sheets + pilot reports -> instantiated registry -> simulated promotion with diffs
	rm -rf /tmp/tripstate-freeze-dry-run && mkdir -p /tmp/tripstate-freeze-dry-run
	python tools/instantiate_eg.py tests/fixtures/od1x_synthetic --registry tests/fixtures/od1x_synthetic/evidence_gated.template.yaml --pilot-reports 'tests/fixtures/od1x_synthetic/pilot_reports/*.json' --out /tmp/tripstate-freeze-dry-run/evidence_gated.synthetic.yaml --date 2026-11-04
	python tools/promote_draft.py --dry-run --registry /tmp/tripstate-freeze-dry-run/evidence_gated.synthetic.yaml --kill-gates tests/fixtures/od1x_synthetic/kill_gates_pass.yaml --out-dir /tmp/tripstate-freeze-dry-run/promotion --date 2026-11-04

calibrate-dry-run:  ## §7.2 harness recovers a deliberately mis-set threshold set on synthetic races
	python tools/calibrate.py --synthetic --out-dir /tmp/tripstate-calibrate-dry-run --date 2026-11-04

evaluate-dry-run:   ## DoD-1…6 report on a synthetic M8 store (two runs for DoD-5)
	python tools/evaluate_release.py --synthetic --out-dir /tmp/tripstate-evaluate-dry-run --date 2026-11-04

od1x-rehearsal:     ## the owner's OD-1x afternoon with synthetic inputs (clip, sheets, scripted stopwatch, proposals)
	python tools/od1x_rehearsal.py --out /tmp/tripstate-od1x-rehearsal

synth-demo:         ## scripted synthetic race through M4->M5->M7->M8 with per-runner scores
	tripstate synth-demo

pilot-demo:         ## synthetic video -> headless seeding with live flags -> both pilot identity paths -> kill-gate report
	rm -rf /tmp/tripstate-pilot-demo && python tools/synth_video.py --out /tmp/tripstate-pilot-demo/synth --duration 8
	python tools/seed_cli.py /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --out /tmp/tripstate-pilot-demo/session --script /tmp/tripstate-pilot-demo/synth/seed_script.json --engine oracle --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json
	python tools/pilot_run.py --video /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --race-json /tmp/tripstate-pilot-demo/synth/race.json --session /tmp/tripstate-pilot-demo/session/session.json --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json --tier-labels /tmp/tripstate-pilot-demo/synth/tier_labels.csv --path seeded --propagator session --human-minutes 4.0 --out /tmp/tripstate-pilot-demo/pilot5/SYNTH-1
	python tools/pilot_run.py --video /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --race-json /tmp/tripstate-pilot-demo/synth/race.json --session /tmp/tripstate-pilot-demo/session/session.json --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json --tier-labels /tmp/tripstate-pilot-demo/synth/tier_labels.csv --path detector --detector oracle --human-minutes 4.0 --out /tmp/tripstate-pilot-demo/pilot5/SYNTH-1
	python tools/pilot_report.py --reports '/tmp/tripstate-pilot-demo/pilot5/SYNTH-1/report_*.json' --md /tmp/tripstate-pilot-demo/pilot5/pilot_report.md

# ---- owner-day helpers and spec maintenance ------------------------------------------------------------------------
od1x-timer:         ## stopwatch usage for OD-1x step 1
	python tools/od1x_timer.py --help

cut-draft:          ## regenerate the draft from the ledger (after adding a rep() edit) and lint it
	python tools/cut_draft.py && python tools/lint_spec.py spec/SPEC-2.0.0-draft.md spec/registers/evidence_gated.yaml

check-draft:        ## verify the committed draft equals the cut
	python tools/cut_draft.py --check
