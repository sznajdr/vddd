#!/usr/bin/env python3
"""Release evaluation DoD-1…6 (§0.2) from the M8 store + golden manifest → data/releases/<version>/evaluation.md.

  evaluate_release.py --store data/store/tripstate.sqlite --manifest data/golden/manifest-v1.0.yaml --version 2.0.0-rc1 \
                      [--store2 path/to/second_run.sqlite] [--producer-version PV] [--ts config/thresholds/TS-x.y.yaml]
  evaluate_release.py --synthetic [--n-heldout 10 --n-dev 12 --n-breaks 12 --recall-misses 2] [--out-dir DIR]

DoD-1 both mask IoUs on held-out; DoD-2 candidate recall + Wilson CI (invalid below 10 observable held-out breaks);
DoD-3 median human-minutes over >= 20 consecutive attempts incl. over_budget; DoD-4 default views exclude
unchartable races (queried); DoD-5 version columns + canonical SHA identity between two stores (--store2);
DoD-6 >= 8/10 held-out pass Q-1…Q-6. Headline with and without Q-7 failures (D-35); per-stratum tables; a §14
changelog row draft. Floors come from the threshold set's `release` namespace (D-18). Logic: tripstate.release.evaluate.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC
from datetime import datetime as _dt
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.config import ThresholdSet, load_default
from tripstate.m8_storage import Store
from tripstate.release.evaluate import changelog_row, evaluate_release, render_markdown


def write_outputs(ev, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "evaluation.md").write_text(render_markdown(ev), encoding="utf-8")
    (out_dir / "evaluation.json").write_text(json.dumps(ev.as_dict(), indent=1, default=str), encoding="utf-8")
    (out_dir / "changelog-row.md").write_text(changelog_row(ev) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store"); ap.add_argument("--store2"); ap.add_argument("--manifest"); ap.add_argument("--version")
    ap.add_argument("--producer-version"); ap.add_argument("--ts")
    ap.add_argument("--synthetic", action="store_true"); ap.add_argument("--n-heldout", type=int, default=10)
    ap.add_argument("--n-dev", type=int, default=12); ap.add_argument("--n-breaks", type=int, default=12)
    ap.add_argument("--recall-misses", type=int, default=2); ap.add_argument("--out-dir")
    ap.add_argument("--date", default=_dt.now(UTC).date().isoformat())
    a = ap.parse_args()
    ts = ThresholdSet.load(a.ts) if a.ts else load_default()
    if a.synthetic:
        from tripstate.release.synthetic_store import build_synthetic_store
        st1, manifest = build_synthetic_store(ts, a.n_heldout, a.n_dev, a.n_breaks, a.recall_misses, created_at="2026-11-04T00:00:00")
        st2, _ = build_synthetic_store(ts, a.n_heldout, a.n_dev, a.n_breaks, a.recall_misses, created_at="2026-11-04T01:00:00")
        ev = evaluate_release(st1, manifest, ts, a.version or "synthetic", a.date, store2=st2)
        out_dir = Path(a.out_dir) if a.out_dir else Path(tempfile.mkdtemp(prefix="evaluate-release-synthetic-"))
        write_outputs(ev, out_dir)
        print(render_markdown(ev))
        print(f"outputs in {out_dir} (SYNTHETIC store — not evidence)")
        return 0
    for req in ("store", "manifest", "version"):
        if not getattr(a, req):
            print(f"missing --{req}")
            return 2
    manifest = yaml.safe_load(Path(a.manifest).read_text(encoding="utf-8"))
    st1 = Store(a.store)
    st2 = Store(a.store2) if a.store2 else None
    ev = evaluate_release(st1, manifest, ts, a.version, a.date, store2=st2, producer_version=a.producer_version)
    out_dir = ROOT / "data" / "releases" / a.version
    write_outputs(ev, out_dir)
    print(render_markdown(ev))
    print(f"wrote {out_dir / 'evaluation.md'}")
    return 0 if ev.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
