"""Write a calibrated threshold set (§7.2 step 3; §9 `threshold_sets.search_provenance`).

Text-level rewrite of the base YAML so comments and `used_in` notes survive: only the winning keys' values change;
`threshold_set_version`, `calibrated: true` and a `search_provenance` block (space, objective, constraints, best
score and components, dev races, seed, date, base set) are written. `ThresholdSet.load` reads the block back."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tripstate.config import ThresholdSet
from tripstate.release.markers import format_value
from tripstate.release.promote import TS_LINE_RE


def provenance(space: dict[str, list], objective: str, constraints: dict[str, float], best: dict, dev_races: list[str],
               date: str, base_version: str, search_space_version: int, method: str = "grid", seed: int = 0,
               extractor_version: str | None = None) -> dict:
    return {"kind": "calibration", "method": method, "search_space_version": search_space_version, "objective": objective,
            "keys": {k: list(v) for k, v in space.items()}, "constraints": dict(constraints),
            "best_score": best.get("headline"), "best_components": {k: best.get(k) for k in ("uncovered_outside_iou", "covered_iou", "rest_macro", "candidate_load_median")},
            "n_candidates": best.get("n_candidates"), "dev_races": list(dev_races), "seed": seed, "date": date,
            "base_threshold_set": base_version, "extractor_version": extractor_version}


def write_threshold_set(base_path: str | Path, out_path: str | Path, version: str, overrides: dict[str, Any],
                        prov: dict, header: str | None = None) -> Path:
    text = Path(base_path).read_text(encoding="utf-8")
    out: list[str] = []
    header_done = False
    pending = dict(overrides)
    for ln in text.splitlines():
        if not header_done:
            if ln.startswith("#"):
                continue
            header_done = True
            out += [f"# Threshold set {version} — calibrated per SPEC §7.2 on {prov.get('date')} from {prov.get('base_threshold_set')}.",
                    "# Only the keys listed under search_provenance.keys were moved; see search_provenance for the space, objective,",
                    "# constraints and dev races. Modules read values through tripstate.config.ThresholdSet."]
            if header:
                out.append(f"# {header}")
        if ln.startswith("threshold_set_version:"):
            out.append(f"threshold_set_version: {version}")
            continue
        if ln.startswith("calibrated:"):
            out.append("calibrated: true")
            continue
        if ln.startswith("search_provenance:"):
            block = yaml.safe_dump({"search_provenance": prov}, sort_keys=False, allow_unicode=True, default_flow_style=False).rstrip("\n")
            out.append(block)
            continue
        m = TS_LINE_RE.match(ln)
        if m and m.group("key") in pending:
            key, val = m.group("key"), m.group("val")
            new = format_value(pending.pop(key), val)
            eg = m.group("eg") or ""
            out.append(f"{m.group('ind')}{key}: {{value: {new}{eg}{m.group('rest')}}}")
            continue
        out.append(ln)
    if pending:
        raise KeyError(f"keys not found in {base_path}: {sorted(pending)}")
    text_out = "\n".join(out) + "\n"
    # a freeze_record block from a frozen base is kept verbatim; it documents lineage. Validate round-trip.
    Path(out_path).write_text(text_out, encoding="utf-8")
    ts = ThresholdSet.load(out_path)
    for k, v in overrides.items():
        if abs(float(ts[k]) - float(v)) > 1e-12:
            raise ValueError(f"round-trip mismatch for {k}: wrote {v}, read {ts[k]}")
    if ts.version != version or not ts.calibrated or not isinstance(ts.search_provenance, dict):
        raise ValueError("written threshold set does not round-trip version/calibrated/search_provenance")
    return Path(out_path)
