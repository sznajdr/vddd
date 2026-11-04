#!/usr/bin/env python3
"""Golden manifest CLI (§6.1). DO NOT run `build` before the 2.0.0 freeze (D-36).

  golden_manifest.py build --candidates data/golden/candidates.csv --seed 20261104 --out data/golden/manifest-v1.0.yaml
  golden_manifest.py validate data/golden/manifest-v1.0.yaml
  golden_manifest.py check-split data/golden/manifest-v1.0.yaml data/golden/hand_charts.csv
  golden_manifest.py diff old.yaml new.yaml

candidates.csv columns: race_id,date,start_format,piste,day_night,field_size,boring,expected_breaks,source_hash[,distance_band,excluded_from_heldout]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.golden import (
    Candidate,
    build_manifest,
    check_split,
    diff_heldout,
    validate_manifest,
)


def read_candidates(path: Path) -> list[Candidate]:
    out = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(Candidate(
                race_id=r["race_id"], date=r["date"], start_format=r["start_format"], piste=r.get("piste") or None,
                day_night=r["day_night"], field_size=int(r["field_size"]),
                boring=r["boring"].strip().lower() in ("1", "true", "yes"), expected_breaks=int(r["expected_breaks"] or 0),
                source_hash=r.get("source_hash") or None, distance_band=r.get("distance_band") or None,
                excluded_from_heldout=(r.get("excluded_from_heldout") or "").strip().lower() in ("1", "true", "yes"),
            ))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--candidates", required=True); b.add_argument("--seed", type=int, required=True)
    b.add_argument("--out", required=True); b.add_argument("--version", default="1.0"); b.add_argument("--reason", default="initial")
    v = sub.add_parser("validate"); v.add_argument("manifest")
    c = sub.add_parser("check-split"); c.add_argument("manifest"); c.add_argument("hand_charts_csv")
    d = sub.add_parser("diff"); d.add_argument("old"); d.add_argument("new")
    a = ap.parse_args()
    if a.cmd == "build":
        from tripstate.version import is_frozen
        if not is_frozen():
            print("REFUSED: golden charting MUST NOT begin before the 2.0.0 freeze (D-36). Run tools/freeze_check.py.")
            return 1
        m = build_manifest(read_candidates(Path(a.candidates)), a.seed, version=a.version, reason=a.reason)
        Path(a.out).write_text(yaml.safe_dump(m, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"wrote {a.out}: {m['n_dev']} dev / {m['n_heldout']} heldout, attempt {m['attempt']}")
        return 0
    if a.cmd == "validate":
        p = validate_manifest(yaml.safe_load(Path(a.manifest).read_text(encoding="utf-8")))
        print("\n".join(p) if p else "manifest OK")
        return 1 if p else 0
    if a.cmd == "check-split":
        m = yaml.safe_load(Path(a.manifest).read_text(encoding="utf-8"))
        with Path(a.hand_charts_csv).open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        p = check_split(m, rows)
        print("\n".join(p) if p else "split consistent")
        return 1 if p else 0
    if a.cmd == "diff":
        o = yaml.safe_load(Path(a.old).read_text(encoding="utf-8")); n = yaml.safe_load(Path(a.new).read_text(encoding="utf-8"))
        dd = diff_heldout(o, n)
        print(dd)
        if (dd["removed"] or dd["added"]) and not dd["reason"]:
            print("held-out membership changed without a recorded reason")
            return 1
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
