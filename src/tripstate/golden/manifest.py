"""Versioned golden manifest (SPEC-2.0.0-draft §6.1; L-28; S-6).

Constraints encoded from §6.1: 30 dev / 10 held-out; >= 5 dev and >= 2 held-out volte_handicap;
>= 10 "boring" races overall; expected observable BREAK starts >= 20 dev / >= 10 held-out;
mixed day/night and both pistes in held-out where the candidate pool has them. Assignment is a
seeded deterministic search; replacements need a recorded reason and a new manifest version;
held-out membership MUST NOT change silently.
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class Candidate:
    race_id: str
    date: str
    start_format: str
    piste: str | None
    day_night: str
    field_size: int
    boring: bool
    expected_breaks: int
    source_hash: str | None = None
    distance_band: str | None = None
    excluded_from_heldout: bool = False   # OD-1x and pilot races: dev-only (protocols)


def _problems(dev: list[Candidate], held: list[Candidate], pool: list[Candidate], n_dev: int, n_heldout: int) -> list[str]:
    p: list[str] = []
    if len(dev) != n_dev or len(held) != n_heldout:
        p.append(f"sizes dev={len(dev)} heldout={len(held)}")
    if sum(c.start_format == "volte_handicap" for c in dev) < 5:
        p.append("dev volte_handicap < 5")
    if sum(c.start_format == "volte_handicap" for c in held) < 2:
        p.append("heldout volte_handicap < 2")
    if sum(c.boring for c in dev + held) < 10:
        p.append("boring races < 10")
    if sum(c.expected_breaks for c in dev) < 20:
        p.append("dev expected breaks < 20")
    if sum(c.expected_breaks for c in held) < 10:
        p.append("heldout expected breaks < 10")
    for attr in ("day_night", "piste"):
        pool_vals = {getattr(c, attr) for c in pool if getattr(c, attr) is not None}
        if len(pool_vals) > 1 and {getattr(c, attr) for c in held} != pool_vals:
            p.append(f"heldout does not cover all {attr} values {sorted(pool_vals)}")
    if any(c.excluded_from_heldout for c in held):
        p.append("heldout contains a dev-only race (OD-1x / pilot)")
    return p


def build_manifest(candidates: list[Candidate], seed: int, n_dev: int = 30, n_heldout: int = 10,
                   max_attempts: int = 5000, version: str = "1.0", reason: str = "initial") -> dict:
    pool = sorted(candidates, key=lambda c: c.race_id)
    if len({c.race_id for c in pool}) != len(pool):
        raise ValueError("duplicate race_id in candidates")
    if len(pool) < n_dev + n_heldout:
        raise ValueError(f"need >= {n_dev + n_heldout} candidates, got {len(pool)}")
    rng = random.Random(seed)
    last: list[str] = []
    for attempt in range(max_attempts):
        order = list(pool)
        rng.shuffle(order)
        eligible_held = [c for c in order if not c.excluded_from_heldout]
        held = eligible_held[:n_heldout]
        held_ids = {c.race_id for c in held}
        dev = [c for c in order if c.race_id not in held_ids][:n_dev]
        last = _problems(dev, held, pool, n_dev, n_heldout)
        if not last:
            entries = sorted(
                [dict(asdict(c), split="dev") for c in dev] + [dict(asdict(c), split="heldout") for c in held],
                key=lambda e: e["race_id"],
            )
            return {
                "manifest_version": version,
                "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "seed": seed,
                "attempt": attempt,
                "reason": reason,
                "n_dev": n_dev,
                "n_heldout": n_heldout,
                "strata_summary": _summary(dev, held),
                "entries": entries,
                "replacements": [],
            }
    raise RuntimeError(f"no assignment satisfied §6.1 after {max_attempts} attempts; last problems: {last}")


def _summary(dev: list[Candidate], held: list[Candidate]) -> dict:
    def count(cs: list[Candidate], attr: str) -> dict:
        out: dict = {}
        for c in cs:
            out[str(getattr(c, attr))] = out.get(str(getattr(c, attr)), 0) + 1
        return dict(sorted(out.items()))
    return {
        split: {"start_format": count(cs, "start_format"), "piste": count(cs, "piste"), "day_night": count(cs, "day_night"),
                "boring": sum(c.boring for c in cs), "expected_breaks": sum(c.expected_breaks for c in cs)}
        for split, cs in (("dev", dev), ("heldout", held))
    }


def validate_manifest(manifest: dict) -> list[str]:
    entries = manifest["entries"]
    cands = [Candidate(**{k: v for k, v in e.items() if k != "split"}) for e in entries]
    dev = [c for c, e in zip(cands, entries) if e["split"] == "dev"]
    held = [c for c, e in zip(cands, entries) if e["split"] == "heldout"]
    p = _problems(dev, held, cands, manifest["n_dev"], manifest["n_heldout"])
    if any(e.get("source_hash") in (None, "") for e in entries):
        p.append("entries without source_hash (required before charting)")
    return p


def check_split(manifest: dict, hand_chart_rows: list[dict]) -> list[str]:
    """S-6: hand_charts.split is a denormalized copy; any mismatch is a write-rejecting error."""
    truth = {e["race_id"]: e["split"] for e in manifest["entries"]}
    problems = []
    for r in hand_chart_rows:
        exp = truth.get(r["race_id"])
        if exp is None:
            problems.append(f"{r['race_id']}: not in manifest")
        elif r.get("split") != exp:
            problems.append(f"{r['race_id']}: split={r.get('split')} but manifest says {exp}")
    return sorted(set(problems))


def diff_heldout(old: dict, new: dict) -> dict:
    o = {e["race_id"] for e in old["entries"] if e["split"] == "heldout"}
    n = {e["race_id"] for e in new["entries"] if e["split"] == "heldout"}
    return {"removed": sorted(o - n), "added": sorted(n - o), "reason": new.get("reason")}
