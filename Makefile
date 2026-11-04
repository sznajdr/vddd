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

cut-draft:
	python tools/cut_draft.py && python tools/lint_spec.py spec/SPEC-2.0.0-draft.md spec/registers/evidence_gated.yaml

check-draft:
	python tools/cut_draft.py --check
