"""Prior-race trip indicators per runner-race row (strictly earlier dates only; §11.3 rule 6)."""
from __future__ import annotations

import math
from collections import defaultdict

from tripstate.signal.corpus import RunnerRow
from tripstate.textparse import parse_notule

INDICATORS = ("parked", "covered", "leader", "wide", "break", "detached")


def indicators_from_text(text: str) -> dict[str, int]:
    """Strict indicators from resolved states; loose ones from candidate sets; events for breaks."""
    r = parse_notule(text, "x", 0)
    res = {s["state"] for s in r.segments if s["mapping_status"] == "resolved" and s["state_kind"] == "base"}
    cand = set()
    for s in r.segments:
        cand.update(s.get("candidate_states") or [])
    out = {
        "parked": int("PARKED" in res), "covered": int(bool(res & {"POCKET", "RAIL_COVERED", "OUTSIDE_COVERED"})),
        "leader": int("LEADER" in res), "wide": int("WIDE" in res), "break": int(bool(r.events)),
        "detached": int(any(s["state"] == "DETACHED" for s in r.segments)),
        "parked_loose": int("PARKED" in cand), "covered_loose": int(bool(cand & {"POCKET", "RAIL_COVERED", "OUTSIDE_COVERED"})),
    }
    return out


def market_logit(rows: list[RunnerRow]) -> dict[tuple[str, str], float]:
    """Normalised implied probability per race -> logit. Rows without odds get the race mean."""
    by_race: dict[str, list[RunnerRow]] = defaultdict(list)
    for r in rows:
        by_race[r.race_id].append(r)
    out = {}
    for rid, rs in by_race.items():
        raw = {r.horse_id: (1.0 / r.odds if r.odds and r.odds > 1.0 else None) for r in rs}
        vals = [v for v in raw.values() if v is not None]
        mean = sum(vals) / len(vals) if vals else 1.0 / max(1, len(rs))
        tot = sum(v if v is not None else mean for v in raw.values())
        for r in rs:
            p = (raw[r.horse_id] if raw[r.horse_id] is not None else mean) / tot
            p = min(max(p, 1e-4), 1 - 1e-4)
            out[(rid, r.horse_id)] = math.log(p / (1 - p))
    return out


def build_features(rows: list[RunnerRow], k_prior: int = 3) -> tuple[list[dict], list[int], list[str], list[str]]:
    """Returns (feature dicts, y=win, race_ids, dates). Features: market_logit, for each indicator
    `<ind>_any` over the last k prior races and `<ind>_last` for the most recent one, n_prior.
    Leakage guard: only rows with a strictly earlier date feed a row's features."""
    ml = market_logit(rows)
    by_horse: dict[str, list[RunnerRow]] = defaultdict(list)
    for r in rows:
        by_horse[r.horse_id].append(r)
    for hist_rows in by_horse.values():
        hist_rows.sort(key=lambda r: (r.date, r.race_id))
    cache: dict[tuple[str, str], dict[str, int]] = {}

    def ind(r: RunnerRow) -> dict[str, int]:
        key = (r.race_id, r.horse_id)
        if key not in cache:
            cache[key] = indicators_from_text(r.notule)
        return cache[key]

    X, y, rids, dates = [], [], [], []
    for r in rows:
        hist = [p for p in by_horse[r.horse_id] if p.date < r.date][-k_prior:]
        f = {"market_logit": ml[(r.race_id, r.horse_id)], "n_prior": len(hist)}
        inds = [ind(p) for p in hist]
        for name in INDICATORS:
            f[f"{name}_any"] = int(any(i[name] for i in inds))
            f[f"{name}_last"] = int(inds[-1][name]) if inds else 0
        f["parked_loose_any"] = int(any(i["parked_loose"] for i in inds))
        X.append(f); y.append(r.win); rids.append(r.race_id); dates.append(r.date)
    return X, y, rids, dates
