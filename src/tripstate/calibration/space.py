"""Declared search space for §7.2 (config/calibration/search-space.yaml). Only listed keys may move; every key must
exist in the base threshold set; an evidence-gated key (eg: true) MUST NOT be searched (D-36: calibration never
substitutes for OD-1x evidence) — the frozen set has no such keys, so this only bites before the freeze."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tripstate.config import ThresholdSet


@dataclass
class SearchSpace:
    version: int
    method: str
    objective: str
    keys: dict[str, list] = field(default_factory=dict)
    used_in: dict[str, str] = field(default_factory=dict)

    @property
    def n_candidates(self) -> int:
        n = 1
        for v in self.keys.values():
            n *= len(v)
        return n

    def validate(self, ts: ThresholdSet, allow_eg: bool = False) -> list[str]:
        problems = []
        for k, vals in self.keys.items():
            if k not in ts.thresholds:
                problems.append(f"search key {k} is not in threshold set {ts.version}")
                continue
            if ts.thresholds[k].eg and not allow_eg:
                problems.append(f"search key {k} is evidence-gated in {ts.version}; calibration cannot replace OD-1x evidence (D-36)")
            if not vals or len(set(map(str, vals))) != len(vals):
                problems.append(f"search key {k}: empty or duplicate grid values")
        if self.method != "grid":
            problems.append(f"search method {self.method!r} not implemented (grid only; Bayesian later)")
        if self.objective != "headline_score":
            problems.append(f"objective {self.objective!r} is not the §6.2 headline")
        return problems


def load_search_space(path: str | Path) -> SearchSpace:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    keys, used = {}, {}
    for k, spec in (raw.get("keys") or {}).items():
        if isinstance(spec, dict):
            keys[k] = list(spec["values"])
            used[k] = spec.get("used_in", "")
        else:
            keys[k] = list(spec)
    return SearchSpace(int(raw.get("search_space_version", 1)), raw.get("method", "grid"), raw.get("objective", "headline_score"), keys, used)
