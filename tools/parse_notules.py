#!/usr/bin/env python3
"""Batch-parse notules into hand_charts/events-shaped JSON (text_parse method, §11).

  parse_notules.py --corpus runners.csv --out data/textparse/parsed.json [--columns race_id=...,notule=...] [--split dev]
Prints a summary: resolved / ambiguous / negated / other-scope counts per family and per state.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.signal import load_corpus_csv
from tripstate.textparse import parse_notule


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True); ap.add_argument("--out", required=True); ap.add_argument("--columns"); ap.add_argument("--split", default="dev")
    a = ap.parse_args()
    cols = dict(kv.split("=", 1) for kv in a.columns.split(",")) if a.columns else None
    rows = load_corpus_csv(Path(a.corpus), cols)
    segs, evs = [], []
    status = Counter(); states = Counter(); fams = Counter()
    for r in rows:
        res = parse_notule(r.notule, r.race_id, r.saddle_no, f"{r.race_id}:{r.saddle_no}")
        for s in res.segments:
            s["split"] = a.split
            status[s["mapping_status"]] += 1
            if s["state"]:
                states[s["state"]] += 1
        for h in res.hits:
            fams[(h.family, "neg" if h.negated else h.scope)] += 1
        segs.extend(res.segments); evs.extend(res.events)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"hand_charts": segs, "events": evs}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} notules -> {len(segs)} segments, {len(evs)} break events")
    print("status:", dict(status)); print("states:", dict(states))
    print("families:", {f"{k[0]}[{k[1]}]": v for k, v in sorted(fams.items())})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
