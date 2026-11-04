.PHONY: setup test lint lint-spec freeze-check freeze-dry-run od1x-timer od1x-rehearsal synth-demo pilot-demo calibrate-dry-run evaluate-dry-run

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
	@if [ -f spec/SPEC-2.0.0.md ]; then python tools/lint_spec.py spec/SPEC-2.0.0.md spec/registers/evidence_gated.yaml; fi

freeze-check:
	python tools/freeze_check.py

# D-36 rehearsal: synthetic OD-1x sheets + pilot reports -> instantiated registry -> simulated promotion in a temp dir.
# Never touches the repository. The real promotion is `python tools/promote_draft.py` once freeze-check passes.
freeze-dry-run:
	rm -rf /tmp/tripstate-freeze-dry-run && mkdir -p /tmp/tripstate-freeze-dry-run
	python tools/instantiate_eg.py tests/fixtures/od1x_synthetic --registry tests/fixtures/od1x_synthetic/evidence_gated.template.yaml --pilot-reports 'tests/fixtures/od1x_synthetic/pilot_reports/*.json' --out /tmp/tripstate-freeze-dry-run/evidence_gated.synthetic.yaml --date 2026-11-04
	python tools/promote_draft.py --dry-run --registry /tmp/tripstate-freeze-dry-run/evidence_gated.synthetic.yaml --kill-gates tests/fixtures/od1x_synthetic/kill_gates_pass.yaml --out-dir /tmp/tripstate-freeze-dry-run/promotion --date 2026-11-04

od1x-timer:
	python tools/od1x_timer.py --help

# C6: the owner's OD-1x afternoon rehearsed with synthetic inputs (clip, sheet templates, scripted stopwatch,
# instantiation proposals on the committed fixture). Nothing it writes is evidence.
od1x-rehearsal:
	python tools/od1x_rehearsal.py --out /tmp/tripstate-od1x-rehearsal

synth-demo:
	tripstate synth-demo

pilot-demo:
	rm -rf /tmp/tripstate-pilot-demo && python tools/synth_video.py --out /tmp/tripstate-pilot-demo/synth --duration 8
	python tools/seed_cli.py /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --out /tmp/tripstate-pilot-demo/session --script /tmp/tripstate-pilot-demo/synth/seed_script.json --engine oracle --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json
	python tools/pilot_run.py --video /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --race-json /tmp/tripstate-pilot-demo/synth/race.json --session /tmp/tripstate-pilot-demo/session/session.json --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json --tier-labels /tmp/tripstate-pilot-demo/synth/tier_labels.csv --path seeded --propagator session --human-minutes 4.0 --out /tmp/tripstate-pilot-demo/pilot5/SYNTH-1
	python tools/pilot_run.py --video /tmp/tripstate-pilot-demo/synth/synth.mp4 --race SYNTH-1 --race-json /tmp/tripstate-pilot-demo/synth/race.json --session /tmp/tripstate-pilot-demo/session/session.json --truth /tmp/tripstate-pilot-demo/synth/synth.mp4.truth.json --tier-labels /tmp/tripstate-pilot-demo/synth/tier_labels.csv --path detector --detector oracle --human-minutes 4.0 --out /tmp/tripstate-pilot-demo/pilot5/SYNTH-1
	python tools/pilot_report.py --reports '/tmp/tripstate-pilot-demo/pilot5/SYNTH-1/report_*.json' --md /tmp/tripstate-pilot-demo/pilot5/pilot_report.md

# §7.2 rehearsal on synthetic races: a deliberately mis-set threshold set must be recovered within one grid step.
# The real run (tools/calibrate.py without --synthetic) is refused while the spec is DRAFT (D-36).
calibrate-dry-run:
	python tools/calibrate.py --synthetic --out-dir /tmp/tripstate-calibrate-dry-run --date 2026-11-04

# DoD-1…6 rehearsal: synthetic M8 store (two runs for DoD-5) + synthetic manifest -> evaluation.md with every DoD line.
evaluate-dry-run:
	python tools/evaluate_release.py --synthetic --out-dir /tmp/tripstate-evaluate-dry-run --date 2026-11-04

cut-draft:
	python tools/cut_draft.py && python tools/lint_spec.py spec/SPEC-2.0.0-draft.md spec/registers/evidence_gated.yaml

check-draft:
	python tools/cut_draft.py --check
