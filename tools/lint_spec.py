#!/usr/bin/env python3
"""Spec hygiene: markdown table column consistency, decision-ID references, EG key presence.

usage: lint_spec.py <spec.md> <evidence_gated.yaml>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def check_tables(text: str, name: str) -> list[str]:
    errs = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*-", lines[i + 1]):
            ncols = len(re.findall(r"(?<!\\)\|", lines[i])) - 1
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                n = len(re.findall(r"(?<!\\)\|", lines[j])) - 1
                if n != ncols:
                    errs.append(f"{name}:{j + 1}: table row has {n} cols, header has {ncols} (unescaped '|'?)")
                j += 1
            i = j
        else:
            i += 1
    return errs


def check_decision_refs(text: str, name: str) -> list[str]:
    log = (ROOT / "spec/decisions/DECISION-LOG.md").read_text(encoding="utf-8")
    known = set(re.findall(r"\bD-(\d{2})\b", log))
    errs = []
    for m in sorted(set(re.findall(r"\bD-(\d{2})\b", text))):
        if m not in known:
            errs.append(f"{name}: references D-{m} which is not in DECISION-LOG.md")
    return errs


def check_eg_keys(eg_path: Path) -> list[str]:
    """Registry keys must be flagged eg: true in the PROVISIONAL set (the frozen set clears the flags by design)."""
    sys.path.insert(0, str(ROOT / "src"))
    from tripstate.config import ThresholdSet
    ts = ThresholdSet.load(ROOT / "config" / "thresholds" / "TS-0.0.0-provisional.yaml")
    eg = yaml.safe_load(eg_path.read_text(encoding="utf-8"))
    errs = []
    for e in eg["entries"]:
        k = e["key"]
        if k in ts.thresholds and not ts.thresholds[k].eg:
            errs.append(f"EG key {k} present in threshold set but not flagged eg: true")
    return errs


def check_frozen_markers(text: str, name: str) -> list[str]:
    """A FROZEN spec carries no evidence-gated or open-decision markers (D-36)."""
    if not re.search(r"^\*\*Status:\*\* FROZEN", text, re.MULTILINE):
        return []
    return [f"{name}:{i}: FROZEN spec still carries a marker: {line.strip()[:80]}"
            for i, line in enumerate(text.splitlines(), 1) if "`[EG" in line or "`[OPEN" in line]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    spec, eg = Path(argv[1]), Path(argv[2])
    text = spec.read_text(encoding="utf-8")
    errs = (check_tables(text, spec.name) + check_decision_refs(text, spec.name) + check_eg_keys(eg)
            + check_frozen_markers(text, spec.name))
    for e in errs:
        print(e)
    print("lint-spec:", "OK" if not errs else f"{len(errs)} problem(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
