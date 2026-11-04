"""Threshold-set loader (D-18, §7.1).

A threshold set is a YAML file under config/thresholds/ with namespaced keys. Every
numeric cutoff that can change an emitted artifact must come from here. Keys flagged
`eg: true` are evidence-gated (D-36): usable for building and testing, not for
calibration or golden evaluation until the registry instantiates them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_NAMESPACES = (
    "geometry", "smoothing", "confidence", "events", "anchors", "ingest",
    "phases", "qc", "yield", "m1_shots", "m2_detect", "m3_track", "m6_events",
)


@dataclass(frozen=True)
class Threshold:
    key: str
    namespace: str
    value: Any
    eg: bool = False
    used_in: str = ""


@dataclass
class ThresholdSet:
    version: str
    spec_version: str
    calibrated: bool
    thresholds: dict[str, Threshold] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> ThresholdSet:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        ts = cls(
            version=raw["threshold_set_version"],
            spec_version=raw["spec_version"],
            calibrated=bool(raw.get("calibrated", False)),
        )
        for ns in _NAMESPACES:
            for key, spec in (raw.get(ns) or {}).items():
                if key in ts.thresholds:
                    raise ValueError(f"duplicate threshold key across namespaces: {key}")
                if isinstance(spec, dict):
                    ts.thresholds[key] = Threshold(
                        key, ns, spec["value"], bool(spec.get("eg", False)), spec.get("used_in", "")
                    )
                else:
                    ts.thresholds[key] = Threshold(key, ns, spec)
        return ts

    def __getitem__(self, key: str) -> Any:
        try:
            return self.thresholds[key].value
        except KeyError as e:
            raise KeyError(f"threshold {key!r} not in {self.version}; add it to the YAML (§7.1)") from e

    def get(self, key: str, default: Any = None) -> Any:
        t = self.thresholds.get(key)
        return default if t is None else t.value

    def evidence_gated_keys(self) -> list[str]:
        return sorted(k for k, t in self.thresholds.items() if t.eg)


def default_threshold_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "thresholds" / "TS-0.0.0-provisional.yaml"


def load_default() -> ThresholdSet:
    return ThresholdSet.load(default_threshold_path())
