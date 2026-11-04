#!/usr/bin/env python3
"""Run the pre-registered signal gate on a runner-race corpus CSV (protocols/SIGNAL-GATE).

  signal_gate.py --corpus data/signal_gate/runners.csv --out data/signal_gate/report.md
                 [--decision protocols/SIGNAL-GATE/decision.yaml] [--columns race_id=...,notule=...] [--kill-gates spec/registers/kill_gates.yaml]
  signal_gate.py --synthetic 0.6 --out /tmp/report.md        # dry run on a synthetic corpus with an injected effect
CSV columns (default names, remappable): race_id, date, horse_id, saddle_no, finish_position, win, placed, odds, notule_runner_texte.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.signal import load_corpus_csv, run_gate, synthetic_corpus
from tripstate.signal.gate import markdown


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus"); ap.add_argument("--synthetic", type=float); ap.add_argument("--out", required=True)
    ap.add_argument("--decision", default=str(ROOT / "protocols/SIGNAL-GATE/decision.yaml")); ap.add_argument("--columns")
    ap.add_argument("--kill-gates"); ap.add_argument("--json")
    a = ap.parse_args()
    decision = yaml.safe_load(Path(a.decision).read_text(encoding="utf-8")) if Path(a.decision).exists() else {}
    if a.synthetic is not None:
        rows = synthetic_corpus(n_horses=150, n_races=900, trip_effect=a.synthetic, seed=1)
    elif a.corpus:
        cols = dict(kv.split("=", 1) for kv in a.columns.split(",")) if a.columns else None
        rows = load_corpus_csv(Path(a.corpus), cols)
    else:
        raise SystemExit("--corpus or --synthetic required")
    rep = run_gate(rows, decision)
    md = markdown(rep)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(md, encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(md)
    if a.kill_gates and a.synthetic is None:
        reg = yaml.safe_load(Path(a.kill_gates).read_text(encoding="utf-8"))
        for g in reg["gates"]:
            if g["id"] == "KG-5":
                g["status"] = {"go": "pass", "no-go": "fail"}.get(rep["verdict"], "not_evaluated")
                g["measured"] = rep.get("holdout", {}).get("logloss_gain")
                g["evidence"] = f"tools/signal_gate.py on {a.corpus}: {rep['verdict']}"
        Path(a.kill_gates).write_text(yaml.safe_dump(reg, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print("kill_gates.yaml KG-5 updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
