.PHONY: setup test lint lint-spec freeze-check od1x-timer

setup:
	pip install -e ".[dev]"

test:
	python -m pytest -q

lint:
	ruff check src tests tools

lint-spec:
	python tools/lint_spec.py spec/SPEC-2.0.0-draft.md spec/registers/evidence_gated.yaml
	python tools/lint_spec.py spec/SPEC-2.0.0-draft-LEDGER.md spec/registers/evidence_gated.yaml
	python tools/cut_draft.py --check

freeze-check:
	python tools/freeze_check.py

od1x-timer:
	python tools/od1x_timer.py --help

synth-demo:
	tripstate synth-demo

pilot-demo:
	rm -rf /tmp/tripstate-pilot-demo && python tools/synth_video.py --out /tmp/tripstate-pilot-demo/synth --duration 8
	python tools/seed_cli.py /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --out /tmp/tripstate-pilot-demo/session --script /tmp/tripstate-pilot-demo/synth/seed_script.json
	python tools/pilot_run.py --video /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --race-json /tmp/tripstate-pilot-demo/synth/race.json --session /tmp/tripstate-pilot-demo/session/session.json --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json --tier-labels /tmp/tripstate-pilot-demo/synth/tier_labels.csv --path seeded --propagator oracle --human-minutes 4.0 --out /tmp/tripstate-pilot-demo/pilot5/SYNTH-1
	python tools/pilot_run.py --video /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --race-json /tmp/tripstate-pilot-demo/synth/race.json --session /tmp/tripstate-pilot-demo/session/session.json --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json --tier-labels /tmp/tripstate-pilot-demo/synth/tier_labels.csv --path detector --detector oracle --human-minutes 4.0 --out /tmp/tripstate-pilot-demo/pilot5/SYNTH-1
	python tools/pilot_report.py --reports '/tmp/tripstate-pilot-demo/pilot5/SYNTH-1/report_*.json' --md /tmp/tripstate-pilot-demo/pilot5/pilot_report.md

cut-draft:
	python tools/cut_draft.py && python tools/lint_spec.py spec/SPEC-2.0.0-draft.md spec/registers/evidence_gated.yaml

check-draft:
	python tools/cut_draft.py --check
