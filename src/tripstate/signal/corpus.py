"""Runner-race rows for the signal gate, CSV loading with a column map, and a synthetic corpus generator."""
from __future__ import annotations

import csv
import datetime as dt
import math
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunnerRow:
    race_id: str
    date: str          # ISO yyyy-mm-dd
    horse_id: str
    saddle_no: int
    finish_position: int | None
    win: int
    placed: int
    odds: float | None     # closing decimal odds
    notule: str            # post-race comment for THIS race (used only as a feature for LATER races)


DEFAULT_COLUMNS = {"race_id": "race_id", "date": "date", "horse_id": "horse_id", "saddle_no": "saddle_no",
                   "finish_position": "finish_position", "win": "win", "placed": "placed", "odds": "odds", "notule": "notule_runner_texte"}


def load_corpus_csv(path: Path, columns: dict[str, str] | None = None) -> list[RunnerRow]:
    cols = dict(DEFAULT_COLUMNS, **(columns or {}))
    rows = []
    with Path(path).open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fp = r.get(cols["finish_position"])
            fp_i = int(fp) if fp not in (None, "", "NA") else None
            win = r.get(cols["win"])
            win_i = int(win) if win not in (None, "", "NA") else int(fp_i == 1) if fp_i else 0
            placed = r.get(cols["placed"])
            placed_i = int(placed) if placed not in (None, "", "NA") else int(fp_i is not None and fp_i <= 3)
            odds = r.get(cols["odds"])
            rows.append(RunnerRow(r[cols["race_id"]], r[cols["date"]][:10], r[cols["horse_id"]], int(r[cols["saddle_no"]] or 0),
                                  fp_i, win_i, placed_i, float(odds) if odds not in (None, "", "NA") else None, r.get(cols["notule"]) or ""))
    return rows


_TEMPLATES = {
    "parked": ["nez au vent en deuxième épaisseur {phase}", "à hauteur de l'animateur {phase}", "sans dos en dehors {phase}"],
    "covered": ["dans un dos {phase}, a fini correctement", "dans le dos de l'animateur {phase}", "à l'abri en deuxième ligne à la corde {phase}"],
    "leader": ["en tête {phase}, a dicté sa loi", "a pris la tête {phase}"],
    "wide": ["en troisième épaisseur {phase}", "tout en dehors {phase}"],
    "break": ["s'est enlevé au départ, remis au trot", "a fait une faute dans le dernier tournant"],
    "neutral": ["a couru correctement", "sans histoire {phase}", "n'a jamais trouvé le dos", "le 7 l'a gêné {phase}", "a rapidement faibli"],
}
_PHASES = ["dès le départ", "à mi-parcours", "dans le dernier tournant", "dans la ligne droite", "sur la fin", ""]


def synthetic_corpus(n_horses: int = 120, n_races: int = 400, field_size: int = 12, trip_effect: float = 0.0,
                     seed: int = 0, start_year: int = 2020, races_per_day: int = 1) -> list[RunnerRow]:
    """Horses with latent ability; each race the market prices ability (plus noise) but wrongly discounts a horse
    whose PREVIOUS race was a parked trip by `trip_effect` logits. With trip_effect > 0 the prior-parked indicator
    carries information beyond the market; with 0 it carries none. Notules are generated from the lexicon."""
    rng = random.Random(seed)
    ability = {f"h{i}": rng.gauss(0, 1) for i in range(n_horses)}
    last_trip: dict[str, str] = {}
    rows: list[RunnerRow] = []
    for k in range(n_races):
        day = k // races_per_day
        date = (dt.date(start_year, 1, 1) + dt.timedelta(days=day)).isoformat()
        horses = rng.sample(list(ability), field_size)
        perf = {}
        market = {}
        trips = {}
        for h in horses:
            trip = rng.choices(["parked", "covered", "leader", "wide", "break", "neutral"], weights=[0.18, 0.3, 0.12, 0.08, 0.07, 0.25])[0]
            trips[h] = trip
            prev_parked = last_trip.get(h) == "parked"
            perf[h] = ability[h] + rng.gauss(0, 1.0)
            market[h] = ability[h] - (trip_effect if prev_parked else 0.0) + rng.gauss(0, 0.5)
        z = sum(math.exp(v) for v in market.values())
        order = sorted(horses, key=lambda h: -perf[h])
        for i, h in enumerate(horses):
            p = math.exp(market[h]) / z
            pos = order.index(h) + 1
            tpl = rng.choice(_TEMPLATES[trips[h]]).format(phase=rng.choice(_PHASES)).replace("  ", " ").strip()
            rows.append(RunnerRow(f"R{k:05d}", date, h, i + 1, pos, int(pos == 1), int(pos <= 3), round(1.0 / max(p, 1e-4) * 1.15, 2), tpl))
            last_trip[h] = trips[h]
    return rows
