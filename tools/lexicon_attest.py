#!/usr/bin/env python3
"""Re-measure [C] attestation of every lexicon family on a notule corpus (§11.1 / §11.4 rule).

  lexicon_attest.py --corpus runners.csv --out spec/registers/lexicon_attestation.yaml [--columns notule=notule_runner_texte]
A family with zero hits is NOT attested and MUST NOT be used until text parsing is re-validated.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.signal import load_corpus_csv
from tripstate.textparse import FAMILIES, PHASE_FAMILIES, normalize


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True); ap.add_argument("--out", required=True); ap.add_argument("--columns")
    a = ap.parse_args()
    cols = dict(kv.split("=", 1) for kv in a.columns.split(",")) if a.columns else None
    rows = load_corpus_csv(Path(a.corpus), cols)
    texts = [normalize(r.notule) for r in rows]
    counts = Counter(); examples = {}
    for f in FAMILIES:
        for t in texts:
            m = f.regex.search(t)
            if m:
                counts[f.id] += 1
                examples.setdefault(f.id, m.group(0))
    phase_counts = Counter()
    for pat, phase, _ in PHASE_FAMILIES:
        import re
        rx = re.compile(pat)
        phase_counts[pat] = sum(1 for t in texts if rx.search(t))
    out = {"measured_at": datetime.now(UTC).isoformat(timespec="seconds"), "corpus_rows": len(rows),
           "families": [{"id": f.id, "target": f.target, "spec_evidence": f.evidence, "hits": counts.get(f.id, 0),
                         "attested": counts.get(f.id, 0) > 0, "example": examples.get(f.id)} for f in FAMILIES],
           "phase_families": [{"pattern": pat, "phase": ph, "hits": phase_counts[pat]} for pat, ph, _ in PHASE_FAMILIES]}
    Path(a.out).write_text(yaml.safe_dump(out, sort_keys=False, allow_unicode=True), encoding="utf-8")
    missing = [f["id"] for f in out["families"] if not f["attested"] and f["target"] not in ("EXCLUDED", "PROXIMITY")]
    print(f"{len(rows)} notules; unattested families: {missing or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
