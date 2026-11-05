#!/usr/bin/env python3
"""Environment fingerprint → versions.determinism_env (SPEC-2.0.0-draft §9, D-32; backlog C3).

  env_fingerprint.py [--seed N] [--batch-size N] [--half-precision] [--weights W.pt ...] [--out fp.json]
                     [--store data/store/tripstate.sqlite --producer-version PV --producer-kind cv_extract [--extractor-version X]]

Prints the key-sorted JSON (stable for an unchanged environment). Values that cannot be read are null; nothing is
guessed and no model is executed. With --store, inserts (or reports an existing) `versions` row carrying it.
Logic: tripstate.m8_storage.determinism.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.m8_storage.determinism import fingerprint, versions_row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int); ap.add_argument("--batch-size", type=int); ap.add_argument("--half-precision", action="store_true")
    ap.add_argument("--weights", nargs="*", default=[]); ap.add_argument("--out")
    ap.add_argument("--store"); ap.add_argument("--producer-version"); ap.add_argument("--producer-kind", default="cv_extract")
    ap.add_argument("--extractor-version"); ap.add_argument("--created-at", default=None)
    a = ap.parse_args()
    kw = {"seed": a.seed, "half_precision": True if a.half_precision else None, "batch_size": a.batch_size, "weights": a.weights}
    fp = fingerprint(**kw)
    text = json.dumps(fp, indent=1, sort_keys=True)
    print(text)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    if a.store:
        if not a.producer_version:
            print("--store needs --producer-version")
            return 2
        from datetime import UTC, datetime

        from tripstate.m8_storage import Store
        st = Store(a.store)
        row = versions_row(a.producer_version, a.producer_kind, a.extractor_version, **kw)
        try:
            st.insert("versions", [row], producer_version=a.producer_version,
                      created_at=a.created_at or datetime.now(UTC).isoformat(timespec="seconds"))
            print(f"inserted versions row {a.producer_version} into {a.store}")
        except sqlite3.IntegrityError:
            print(f"versions row {a.producer_version} already exists in {a.store}; not overwritten")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
