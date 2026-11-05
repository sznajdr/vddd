#!/usr/bin/env python3
"""Export calibration inputs (backlog C8): per manifest race, a geometry sidecar + the human hand chart.

  export_calibration_inputs.py --frames-dir data/frames --store data/store/tripstate.sqlite \
      --manifest data/golden/manifest-v1.0.yaml --out data/calibration [--split dev|heldout|all] \
      [--human-producer PV] [--races R1 R2 ...]

Inputs per race: <frames-dir>/<race_id>.frames.json (tripstate.m4.frames/1, written by the pipeline from M4's
FrameGeometry list — tripstate.m4_geometry.frames_to_json) and the store's `hand_charts` rows (method human_chart).
Outputs: <out>/<race_id>.geometry.json (tripstate.calibration.sidecar.RaceGeometry) + <race_id>.hand_chart.json.
Refuses: a race missing from the manifest or without a frames file / hand chart, a frames file whose race_id differs
from its name, a hand-chart `split` that disagrees with the manifest (S-6), and more than one human producer for a
race unless --human-producer selects one. Exports nothing when any race is refused (all or nothing).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tripstate.calibration.sidecar import RaceGeometry
from tripstate.m4_geometry import frames_from_json
from tripstate.m8_storage import Store

HAND_COLUMNS = ("race_id", "saddle_no", "seg_id", "state_kind", "state", "covered", "lead_uncovered_outside",
                "lead_uncovered_outside_ambiguous", "tier_attr", "end_attr", "method", "t_start_frac", "t_end_frac",
                "confidence", "visibility", "start_truncated", "end_truncated", "charter_minutes", "split", "producer_version")


def export(frames_dir: Path, store: Store, manifest: dict, out: Path, split: str = "all", human_producer: str | None = None,
           races: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Returns (exported race ids, problems). Writes only when there are no problems."""
    split_of = {e["race_id"]: e["split"] for e in manifest["entries"]}
    wanted = sorted(races) if races else sorted(r for r, s in split_of.items() if split in ("all", s))
    problems: list[str] = []
    plan: list[tuple[str, RaceGeometry, list[dict]]] = []
    hand = defaultdict(list)
    for r in store.rows("hand_charts"):
        if r["method"] == "human_chart":
            hand[r["race_id"]].append(r)
    for rid in wanted:
        if rid not in split_of:
            problems.append(f"{rid}: not in the golden manifest")
            continue
        fp = frames_dir / f"{rid}.frames.json"
        if not fp.exists():
            problems.append(f"{rid}: missing {fp.name} in {frames_dir}")
            continue
        try:
            frames, meta = frames_from_json(fp.read_text(encoding="utf-8"))
        except (ValueError, KeyError, TypeError) as e:
            problems.append(f"{rid}: unreadable frames file ({e})")
            continue
        if meta["race_id"] != rid:
            problems.append(f"{rid}: frames file carries race_id {meta['race_id']!r}")
            continue
        rows = hand.get(rid, [])
        producers = sorted({r["producer_version"] for r in rows})
        if not rows:
            problems.append(f"{rid}: no human hand chart in the store")
            continue
        if human_producer:
            rows = [r for r in rows if r["producer_version"] == human_producer]
            if not rows:
                problems.append(f"{rid}: no hand chart from producer {human_producer!r} (have {producers})")
                continue
        elif len(producers) > 1:
            problems.append(f"{rid}: {len(producers)} human producers {producers}; choose one with --human-producer")
            continue
        bad_split = sorted({r["split"] for r in rows if r["split"] != split_of[rid]})
        if bad_split:
            problems.append(f"{rid}: hand_charts.split {bad_split} disagrees with the manifest ({split_of[rid]}) — S-6")
            continue
        geom = RaceGeometry.from_projector(rid, frames, meta["saddles"], meta["t0_video_s"], meta["tend_video_s"],
                                           meta["intervals"], meta["box_heights"], producer=meta["producer"])
        plan.append((rid, geom, [{k: r.get(k) for k in HAND_COLUMNS} for r in rows]))
    if problems:
        return [], problems
    out.mkdir(parents=True, exist_ok=True)
    for rid, geom, rows in plan:
        (out / f"{rid}.geometry.json").write_text(geom.to_json(), encoding="utf-8")
        (out / f"{rid}.hand_chart.json").write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return [rid for rid, _, _ in plan], []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames-dir", required=True); ap.add_argument("--store", required=True); ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--split", default="all", choices=["all", "dev", "heldout"])
    ap.add_argument("--human-producer"); ap.add_argument("--races", nargs="*")
    a = ap.parse_args()
    for p in (a.frames_dir, a.store, a.manifest):
        if not Path(p).exists():
            print(f"missing input: {p}")
            return 2
    manifest = yaml.safe_load(Path(a.manifest).read_text(encoding="utf-8"))
    done, problems = export(Path(a.frames_dir), Store(a.store), manifest, Path(a.out), a.split, a.human_producer, a.races)
    if problems:
        print("REFUSED (nothing exported):\n  - " + "\n  - ".join(problems))
        return 1
    print(f"exported {len(done)} races to {a.out}: {', '.join(done)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
