#!/usr/bin/env python3
"""§7.2 calibration CLI. HARD GUARD: refuses unless the spec is FROZEN (tripstate.version.is_frozen()) and the golden
manifest exists; evidence-gated keys are never searched (D-36).

  calibrate.py --ts config/thresholds/TS-2.0.0-frozen.yaml --space config/calibration/search-space.yaml \
               --dev-dir data/calibration --manifest data/golden/manifest-v1.0.yaml --version TS-2.1.0 \
               --out config/thresholds/TS-2.1.0.yaml [--heldout] [--extractor-version EXTR] [--date YYYY-MM-DD]
  calibrate.py --synthetic [--perturb cover_lat_sw=0.5 --perturb same_tier_sw=0.4] [--out-dir DIR] [--noise-sd 0.005]

Dev-dir layout: <race_id>.geometry.json (tripstate.calibration.sidecar.RaceGeometry) + <race_id>.hand_chart.json
(hand_charts rows). Races are taken from the manifest split: dev for the search, heldout only with --heldout, once.
--synthetic runs the loop on synthetic races with a deliberately mis-set base threshold set and must recover the
true values within one grid step; it writes its outputs to a temp dir and exits 1 if recovery fails.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC
from datetime import datetime as _dt
from itertools import pairwise
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.calibration.holdout import changelog_row, evaluate_heldout
from tripstate.calibration.search import DevRace, candidate_ts, evaluate_candidate, grid_search
from tripstate.calibration.sidecar import RaceGeometry
from tripstate.calibration.space import SearchSpace, load_search_space
from tripstate.calibration.synthetic import SYNTHETIC_SPACE, synthetic_races
from tripstate.calibration.tsio import provenance, write_threshold_set
from tripstate.config import ThresholdSet, default_threshold_path


def parse_perturb(items: list[str]) -> dict[str, float]:
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        out[k.strip()] = float(v)
    return out


def load_races(dev_dir: Path, manifest: dict, split: str) -> list[DevRace]:
    ids = [e["race_id"] for e in manifest["entries"] if e["split"] == split]
    races = []
    for rid in ids:
        g, h = dev_dir / f"{rid}.geometry.json", dev_dir / f"{rid}.hand_chart.json"
        if not (g.exists() and h.exists()):
            continue
        rows = json.loads(h.read_text(encoding="utf-8"))
        bad = [r for r in rows if r.get("split") not in (None, split)]
        if bad:
            raise SystemExit(f"{rid}: hand chart split disagrees with the manifest (S-6)")
        races.append(DevRace(rid, RaceGeometry.from_json(g.read_text(encoding="utf-8")), rows, split))
    return races


def run_synthetic(a) -> int:
    base_true = ThresholdSet.load(a.ts or default_threshold_path())
    perturb = parse_perturb(a.perturb) or {"cover_lat_sw": 0.5, "same_tier_sw": 0.4}
    base = candidate_ts(base_true, perturb)                     # the deliberately mis-set set the harness starts from
    dev, held = synthetic_races(base_true, noise_sd=a.noise_sd)
    space = SYNTHETIC_SPACE if not a.space else load_search_space(a.space).keys
    out_dir = Path(a.out_dir) if a.out_dir else Path(tempfile.mkdtemp(prefix="calibrate-synthetic-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    before = evaluate_candidate(base, {}, dev)
    print(f"synthetic dry run: base (mis-set) {perturb} -> dev headline {before.headline:.3f}, feasible={before.feasible}")
    res = grid_search(base, space, dev, progress=lambda i, r: print(f"  [{i:3d}/{len(space['cover_lat_sw']) * len(space['same_tier_sw']) if set(space) == set(SYNTHETIC_SPACE) else '?'}] {r.overrides} headline={r.headline if r.headline is None else round(r.headline, 4)} {'ok' if r.feasible else 'infeasible'}"))
    (out_dir / "search.json").write_text(json.dumps(res.as_dict(), indent=1), encoding="utf-8")
    if res.best is None:
        print("no feasible candidate:", res.reasons)
        return 1
    print(f"best: {res.best.overrides} headline={res.best.headline:.4f} load_median={res.best.candidate_load_median}")
    ok = True
    for k, vals in space.items():
        truth = float(base_true[k])
        step = min(abs(b - c) for b, c in pairwise(vals)) if len(vals) > 1 else 0.0
        got = float(res.best.overrides[k])
        within = abs(got - truth) <= step + 1e-9
        ok &= within
        print(f"  {k}: true {truth} recovered {got} (grid step {step:g}) -> {'OK' if within else 'MISSED'}")
    prov = provenance(space, "headline_score", res.constraints, dict(res.best.as_dict(), n_candidates=len(res.results)),
                      [r.race_id for r in dev], a.date, base.version, 0, extractor_version="synthetic")
    ts_path = write_threshold_set(base_true.path or default_threshold_path(), out_dir / "TS-synthetic-calibrated.yaml",
                                  "TS-synthetic-calibrated", res.best.overrides, prov, header="SYNTHETIC dry run — not a real calibration")
    ho = evaluate_heldout(ThresholdSet.load(ts_path), held, res.best.headline)
    (out_dir / "heldout.json").write_text(json.dumps(ho.as_dict(), indent=1), encoding="utf-8")
    row = changelog_row("synthetic", a.date, "TS-synthetic-calibrated", "synthetic", ho)
    (out_dir / "changelog-row.md").write_text(row + "\n", encoding="utf-8")
    print(f"held-out (one shot): headline {ho.heldout.headline if ho.heldout.headline is None else round(ho.heldout.headline, 4)} gap {ho.gap_pt if ho.gap_pt is None else round(ho.gap_pt, 2)} pt -> {ho.verdict}")
    print(row)
    print(f"outputs in {out_dir} (threshold set, search.json, heldout.json, changelog-row.md)")
    print("SYNTHETIC DRY RUN OK" if ok else "SYNTHETIC DRY RUN FAILED: recovery outside one grid step")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ts"); ap.add_argument("--space"); ap.add_argument("--dev-dir"); ap.add_argument("--manifest")
    ap.add_argument("--version"); ap.add_argument("--out"); ap.add_argument("--heldout", action="store_true")
    ap.add_argument("--extractor-version", default=None)
    ap.add_argument("--synthetic", action="store_true"); ap.add_argument("--perturb", action="append", default=[])
    ap.add_argument("--out-dir"); ap.add_argument("--noise-sd", type=float, default=0.005)
    ap.add_argument("--date", default=_dt.now(UTC).date().isoformat())
    a = ap.parse_args()
    if a.synthetic:
        return run_synthetic(a)
    from tripstate.version import SPEC_STATUS, is_frozen
    if not is_frozen():
        print(f"REFUSED: calibration MUST NOT run before the 2.0.0 freeze (D-36); SPEC_STATUS = {SPEC_STATUS}. "
              "Use --synthetic for the dry run.")
        return 1
    if not a.manifest or not Path(a.manifest).exists():
        print("REFUSED: the golden manifest does not exist (§7.2 step 1: freeze the dev/held-out split first).")
        return 1
    for req in ("ts", "space", "dev_dir", "version", "out"):
        if not getattr(a, req):
            print(f"missing --{req.replace('_', '-')}")
            return 2
    base = ThresholdSet.load(a.ts)
    space: SearchSpace = load_search_space(a.space)
    problems = space.validate(base)
    if base.evidence_gated_keys():
        problems.append(f"base threshold set {base.version} still has evidence-gated keys {base.evidence_gated_keys()}: calibrate from the frozen set")
    if problems:
        print("REFUSED:\n  - " + "\n  - ".join(problems))
        return 1
    manifest = yaml.safe_load(Path(a.manifest).read_text(encoding="utf-8"))
    dev = load_races(Path(a.dev_dir), manifest, "dev")
    if not dev:
        print("REFUSED: no dev races with geometry + hand chart in", a.dev_dir)
        return 1
    print(f"grid search: {space.n_candidates} candidates x {len(dev)} dev races")
    res = grid_search(base, space.keys, dev, progress=lambda i, r: print(f"  [{i}/{space.n_candidates}] {r.overrides} headline={r.headline} {'ok' if r.feasible else 'infeasible'}"))
    Path(a.out).with_suffix(".search.json").write_text(json.dumps(res.as_dict(), indent=1), encoding="utf-8")
    if res.best is None:
        print("NO WINNER:", *res.reasons, sep="\n  ")
        return 1
    prov = provenance(space.keys, space.objective, res.constraints, dict(res.best.as_dict(), n_candidates=len(res.results)),
                      [r.race_id for r in dev], a.date, base.version, space.version, extractor_version=a.extractor_version)
    write_threshold_set(a.ts, a.out, a.version, res.best.overrides, prov)
    print(f"wrote {a.out}: {res.best.overrides} dev headline {res.best.headline:.4f}")
    if a.heldout:
        held = load_races(Path(a.dev_dir), manifest, "heldout")
        ho = evaluate_heldout(ThresholdSet.load(a.out), held, res.best.headline)
        Path(a.out).with_suffix(".heldout.json").write_text(json.dumps(ho.as_dict(), indent=1), encoding="utf-8")
        row = changelog_row(base.spec_version, a.date, a.version, a.extractor_version or "—", ho)
        Path(a.out).with_suffix(".changelog-row.md").write_text(row + "\n", encoding="utf-8")
        print(row)
        print("held-out verdict:", ho.verdict, *ho.notes)
        return 0 if ho.verdict == "accept" else 1
    print("held-out not evaluated (run once, with --heldout, at the declared freeze evaluation — §6.3).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
