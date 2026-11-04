"""Release evaluation DoD-1…6 (SPEC-2.0.0-draft §0.2, §6.2–6.3; D-27, D-31, D-35) from the M8 store + golden manifest.

Every DoD line carries a status in {pass, fail, invalid, not_evaluated} and the reason: an undersized fixture makes
a line `invalid` (never a pass by convention, §6.3). Numbers come from the threshold set's `release` namespace
(D-18). The headline is reported twice, with and without Q-7 (`over_budget`) failures (D-35); per-stratum tables
(day/night × field band × start_format × piste) are REQUIRED (§6.3). Reads use the store's diagnostic override
only to score unchartable-but-eligible attempts; the default views are what DoD-4 inspects."""
from __future__ import annotations

import statistics as st
from collections import defaultdict
from dataclasses import dataclass, field

from tripstate.config import ThresholdSet
from tripstate.evaluation.metrics import break_candidate_recall, wilson_ci
from tripstate.evaluation.scoring import RaceScore, score_race, score_set
from tripstate.golden.manifest import validate_manifest
from tripstate.m7_qc.gates import stratum_yield
from tripstate.m8_storage.store import Store

Q7_ONLY = {"over_budget"}
CV_TABLES = ("state_segments", "events", "qc", "runner_qc", "shots", "tracklets", "id_assignments", "race_anchors", "shot_calibrations")


@dataclass
class DoD:
    id: str
    status: str                    # pass | fail | invalid | not_evaluated
    summary: str
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"id": self.id, "status": self.status, "summary": self.summary, "details": self.details}


@dataclass
class ReleaseEvaluation:
    version: str
    date: str
    spec_version: str
    producer_version: str | None
    extractor_versions: list[str]
    threshold_set_versions: list[str]
    heldout_ids: list[str]
    dods: list[DoD]
    headline_with_q7: dict
    headline_without_q7: dict
    strata_yield: dict
    strata_headline: dict
    notes: list[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return all(d.status == "pass" for d in self.dods)

    def dod(self, id_: str) -> DoD:
        return next(d for d in self.dods if d.id == id_)

    def as_dict(self) -> dict:
        return {"version": self.version, "date": self.date, "spec_version": self.spec_version, "producer_version": self.producer_version,
                "extractor_versions": self.extractor_versions, "threshold_set_versions": self.threshold_set_versions,
                "heldout_ids": self.heldout_ids, "dods": [d.as_dict() for d in self.dods], "headline_with_q7": self.headline_with_q7,
                "headline_without_q7": self.headline_without_q7, "strata_yield": self.strata_yield, "strata_headline": self.strata_headline,
                "notes": self.notes, "v1_complete": self.complete}


def _field_band(n: int) -> str:
    return "<=10" if n <= 10 else "11-14" if n <= 14 else ">14"


def _charted_from_gaps(gaps: list[dict]) -> list[tuple[float, float]]:
    """Charted race fraction = [0, 1] minus the hand chart's SHOT_GAP intervals."""
    ivs = [(0.0, 1.0)]
    for g in sorted(gaps, key=lambda r: r["t_start_frac"]):
        a, b = g["t_start_frac"], g["t_end_frac"] if g["t_end_frac"] is not None else 1.0
        nxt = []
        for x, y in ivs:
            if b <= x or a >= y:
                nxt.append((x, y))
            else:
                if a > x:
                    nxt.append((x, a))
                if b < y:
                    nxt.append((b, y))
        ivs = nxt
    return [iv for iv in ivs if iv[1] > iv[0]]


def _observable_at(truth_rows: list[dict], saddle: int, t: float) -> bool:
    return any(r["saddle_no"] == saddle and r["state_kind"] == "base" and r["state"] != "NOT_VISIBLE"
               and r["t_start_frac"] <= t < r["t_end_frac"] for r in truth_rows)


def evaluate_release(store: Store, manifest: dict, ts: ThresholdSet, version: str, date: str,
                     store2: Store | None = None, producer_version: str | None = None) -> ReleaseEvaluation:
    from tripstate.version import SPEC_VERSION

    notes: list[str] = []
    mp = validate_manifest(manifest)
    if mp:
        notes.append("golden manifest does not validate: " + "; ".join(mp))
    heldout = sorted(e["race_id"] for e in manifest["entries"] if e["split"] == "heldout")
    where = {"producer_version": producer_version} if producer_version else None
    qc_rows = {r["race_id"]: r for r in store.rows("qc", where)}
    races = {r["race_id"]: r for r in store.rows("races")}
    runners_n: dict[str, int] = defaultdict(int)
    for r in store.rows("runners"):
        runners_n[r["race_id"]] += 1
    anchors = {r["race_id"]: r for r in store.rows("race_anchors", where)}
    hand = defaultdict(list)
    for r in store.rows("hand_charts"):
        hand[r["race_id"]].append(r)
    events = defaultdict(list)
    for r in store.rows("events"):
        # Human truth has its own producer; scope only extracted candidates to the selected run.
        if producer_version and r["method"] == "cv_extract" and r["producer_version"] != producer_version:
            continue
        events[r["race_id"]].append(r)
    segs = defaultdict(list)
    for r in store.state_segments(producer_version=producer_version, include_unchartable=True):
        segs[r["race_id"]].append(r)
    extractor_versions = sorted({r["extractor_version"] for rows in segs.values() for r in rows if r.get("extractor_version")})
    ts_versions = sorted({r["threshold_set_version"] for rows in segs.values() for r in rows if r.get("threshold_set_version")})

    # --- eligibility of held-out races (§6.3: Q-1…Q-6 void accuracy; Q-7 does not) -----------------
    q16_pass, without_q7, missing_qc = [], [], []
    for rid in heldout:
        q = qc_rows.get(rid)
        if q is None:
            missing_qc.append(rid)
            continue
        codes = set(q["failure_codes"] or [])
        if codes <= Q7_ONLY:
            q16_pass.append(rid)
            if not codes:
                without_q7.append(rid)
    s6 = [rid for rid in heldout if any(r.get("split") != "heldout" for r in hand.get(rid, []))]
    if s6:
        notes.append(f"S-6 violation: hand_charts.split disagrees with the manifest for {s6}")
    missing_charts = [rid for rid in q16_pass if not any(r["method"] == "human_chart" for r in hand.get(rid, []))]
    truth_problems = []
    if missing_charts:
        truth_problems.append(f"missing human hand charts for eligible held-out races {missing_charts}")
    if s6:
        truth_problems.append(f"S-6 split mismatch for held-out races {s6}")
    truth_invalid = "; ".join(truth_problems)

    # --- DoD-6 ----------------------------------------------------------------------------------
    n_req, min_pass = int(ts["dod6_heldout_n"]), int(ts["dod6_min_pass"])
    d6_details = {"n_heldout_manifest": len(heldout), "n_with_qc": len(heldout) - len(missing_qc), "n_pass_q1_q6": len(q16_pass),
                  "passing": q16_pass, "missing_qc": missing_qc, "required": f">= {min_pass} of {n_req}"}
    if len(heldout) != n_req:
        d6 = DoD("DoD-6", "invalid", f"held-out set has {len(heldout)} races in the manifest, §6.1 requires {n_req}", d6_details)
    elif len(q16_pass) >= min_pass:
        d6 = DoD("DoD-6", "pass", f"{len(q16_pass)}/{n_req} held-out races pass Q-1…Q-6", d6_details)
    else:
        d6 = DoD("DoD-6", "fail", f"only {len(q16_pass)}/{n_req} held-out races pass Q-1…Q-6 (need {min_pass})", d6_details)

    # --- headline, dual (D-35) ------------------------------------------------------------------
    def scores_for(ids: list[str]) -> list[RaceScore]:
        out = []
        for rid in ids:
            truth = [r for r in hand.get(rid, []) if r["method"] == "human_chart"]
            if not truth:
                notes.append(f"{rid}: no hand chart in the store; excluded from accuracy")
                continue
            gaps = [e for e in events.get(rid, []) if e["type"] == "SHOT_GAP" and e["method"] == "human_chart"]
            out.append(score_race(rid, segs.get(rid, []), truth, _charted_from_gaps(gaps)))
        return out
    with_q7_scores = scores_for(q16_pass)
    without_scores = [s for s in with_q7_scores if s.race_id in without_q7]
    hw, hwo = score_set(with_q7_scores), score_set(without_scores)

    # --- DoD-1 ----------------------------------------------------------------------------------
    floor = float(ts["dod1_mask_iou_min"])
    d1_details = {"with_q7": hw.as_dict(), "without_q7": hwo.as_dict(), "floor": floor,
                  "per_race": {s.race_id: {"uncovered_outside_iou": s.uncovered_outside_iou, "covered_iou": s.covered_iou, "rest_macro": s.rest_macro} for s in with_q7_scores}}
    if d6.status != "pass":
        d1 = DoD("DoD-1", "invalid", f"invalid because DoD-6 is {d6.status} (§6.3)", d1_details)
    elif truth_invalid:
        d1 = DoD("DoD-1", "invalid", truth_invalid, d1_details)
    elif hw.uncovered_outside_iou is None or hw.covered_iou is None:
        d1 = DoD("DoD-1", "invalid", "a DoD-1 mask has an empty union across the held-out set; revise the golden fixtures (D-28)", d1_details)
    elif hw.uncovered_outside_iou >= floor and hw.covered_iou >= floor:
        d1 = DoD("DoD-1", "pass", f"uncovered-outside IoU {hw.uncovered_outside_iou:.3f}, covered IoU {hw.covered_iou:.3f} ≥ {floor} on {hw.n_races} races (Q-7 failures included)", d1_details)
    else:
        d1 = DoD("DoD-1", "fail", f"uncovered-outside IoU {hw.uncovered_outside_iou:.3f}, covered IoU {hw.covered_iou:.3f} vs floor {floor}", d1_details)

    # --- DoD-2 ----------------------------------------------------------------------------------
    tol_s = float(ts["break_match_tolerance_s"])
    n_truth = matched = 0
    loads: list[int] = []
    unanchored: list[str] = []
    for rid in q16_pass:
        a = anchors.get(rid)
        dur = (a["tend_video_s"] - a["t0_video_s"]) if a and a.get("t0_video_s") is not None and a.get("tend_video_s") is not None else None
        ev = events.get(rid, [])
        truth_rows = hand.get(rid, [])
        gaps = _charted_from_gaps([e for e in ev if e["type"] == "SHOT_GAP" and e["method"] == "human_chart"])
        truth_b = [e for e in ev if e["type"] == "BREAK" and e["method"] == "human_chart"
                   and any(x <= e["t_start_frac"] < y for x, y in gaps) and _observable_at(truth_rows, e["saddle_no"], e["t_start_frac"])]
        cands = [e for e in ev if e["type"] == "BREAK" and e["method"] == "cv_extract"]
        loads.append(len(cands))
        if dur is None:
            if truth_b:
                unanchored.append(rid)
            continue
        for s in sorted({e["saddle_no"] for e in truth_b}):
            m, n, _ = break_candidate_recall([e["t_start_frac"] * dur for e in cands if e["saddle_no"] == s],
                                             [e["t_start_frac"] * dur for e in truth_b if e["saddle_no"] == s], tol_s)
            matched += m
            n_truth += n
    rec_min, min_breaks = float(ts["dod2_break_recall_min"]), int(ts["dod2_min_heldout_breaks"])
    p, lo, hi = wilson_ci(matched, n_truth) if n_truth else (None, None, None)
    d2_details = {"matched": matched, "n_observable_truth_breaks": n_truth, "point": p, "wilson_95": [lo, hi], "floor": rec_min,
                  "candidate_load_median": st.median(loads) if loads else None, "unanchored_races_skipped": unanchored}
    if unanchored:
        notes.append(f"DoD-2: races without timeline anchors cannot convert fractions to seconds and were skipped: {unanchored}")
    if d6.status != "pass":
        d2 = DoD("DoD-2", "invalid", f"invalid because DoD-6 is {d6.status} (§6.3)", d2_details)
    elif truth_invalid:
        d2 = DoD("DoD-2", "invalid", truth_invalid, d2_details)
    elif n_truth < min_breaks:
        d2 = DoD("DoD-2", "invalid", f"only {n_truth} observable held-out BREAK starts (< {min_breaks}); manifest revision required (§6.1)", d2_details)
    elif p >= rec_min:
        d2 = DoD("DoD-2", "pass", f"candidate recall {matched}/{n_truth} = {p:.3f} (Wilson 95% [{lo:.2f}, {hi:.2f}]) ≥ {rec_min}; point estimate, not a certification (D-31)", d2_details)
    else:
        d2 = DoD("DoD-2", "fail", f"candidate recall {matched}/{n_truth} = {p:.3f} (Wilson 95% [{lo:.2f}, {hi:.2f}]) < {rec_min}", d2_details)

    # --- DoD-3 ----------------------------------------------------------------------------------
    order = sorted(qc_rows.values(), key=lambda q: (races.get(q["race_id"], {}).get("date", ""), races.get(q["race_id"], {}).get("meeting", ""),
                                                   races.get(q["race_id"], {}).get("race_no", 0), q["race_id"]))
    minutes = [q["human_minutes"] for q in order if q.get("human_minutes") is not None]
    target, min_att = float(ts["dod3_median_target_min"]), int(ts["dod3_min_attempts"])
    med = st.median(minutes) if minutes else None
    d3_details = {"n_attempts": len(minutes), "median_minutes": med, "target": target, "min_attempts": min_att,
                  "n_over_budget": sum(1 for q in order if "over_budget" in (q["failure_codes"] or []))}
    if len(minutes) < min_att:
        d3 = DoD("DoD-3", "invalid", f"{len(minutes)} eligible attempts with logged human-minutes (< {min_att})", d3_details)
    elif med <= target:
        d3 = DoD("DoD-3", "pass", f"median {med:.2f} min over {len(minutes)} consecutive attempts (incl. over_budget) ≤ {target:g}", d3_details)
    else:
        d3 = DoD("DoD-3", "fail", f"median {med:.2f} min over {len(minutes)} attempts > {target:g}", d3_details)

    # --- DoD-4 ----------------------------------------------------------------------------------
    unchartable = {rid for rid, q in qc_rows.items() if not q["chartable"]}
    view_ids = {r[0] for r in store.conn.execute("SELECT DISTINCT race_id FROM v_state_segments_chartable")}
    export_ids = {r["race_id"] for r in store.feature_export(producer_version=producer_version)}
    leak = sorted((view_ids | export_ids) & unchartable)
    try:
        store.feature_export(include_unchartable=True)
        override_rejected = False
    except TypeError:
        override_rejected = True
    d4_details = {"n_unchartable": len(unchartable), "leaked": leak, "override_rejected": override_rejected}
    if not leak and override_rejected:
        d4 = DoD("DoD-4", "pass", f"no rows from {len(unchartable)} unchartable races in the default view / feature export; override rejected structurally", d4_details)
    else:
        d4 = DoD("DoD-4", "fail", f"unchartable races in default views: {leak}; override rejected: {override_rejected}", d4_details)

    # --- DoD-5 ----------------------------------------------------------------------------------
    missing_ver: dict[str, int] = {}
    for t in CV_TABLES:
        cols = store.columns(t)
        if "extractor_version" not in cols:
            continue
        n_bad = 0
        for r in store.rows(t, where if "producer_version" in cols and where else None):
            if "method" in cols and r.get("method") not in (None, "cv_extract"):
                continue
            if not r.get("extractor_version") or not r.get("threshold_set_version"):
                n_bad += 1
        if n_bad:
            missing_ver[t] = n_bad
    n_no_art = 0
    for t in store.tables():
        cols = store.columns(t)
        if "schema_version" in cols:
            n_no_art += sum(1 for r in store.rows(t) if not r.get("schema_version") or not r.get("producer_version"))
    if store2 is None:
        ident = None
        diff_tables: list[str] = []
    else:
        a, b = store.canonical_all(producer_version), store2.canonical_all(producer_version)
        diff_tables = sorted(t for t in a if a[t] != b.get(t))
        ident = not diff_tables
    d5_details = {"rows_missing_extractor_or_ts_version": missing_ver, "rows_missing_schema_or_producer_version": n_no_art,
                  "canonical_identity": ident, "tables_differing": diff_tables}
    if missing_ver or n_no_art:
        d5 = DoD("DoD-5", "fail", f"version columns missing: {missing_ver or ''} {n_no_art or ''}".strip(), d5_details)
    elif ident is None:
        d5 = DoD("DoD-5", "not_evaluated", "version columns complete; canonical identity needs a second run of the same inputs (--store2)", d5_details)
    elif ident:
        d5 = DoD("DoD-5", "pass", "version columns complete; canonical SHA-256 identical per table between the two runs", d5_details)
    else:
        d5 = DoD("DoD-5", "fail", f"canonical payload differs between runs in {diff_tables}", d5_details)

    # --- strata (§6.3; D-35) --------------------------------------------------------------------
    def stratum(rid: str) -> tuple:
        q, r = qc_rows.get(rid, {}), races.get(rid, {})
        return (q.get("stratum") or "?", _field_band(runners_n.get(rid, 0)), r.get("start_format") or "?", r.get("piste") or "?")
    sy = stratum_yield([(stratum(rid), bool(q["chartable"])) for rid, q in qc_rows.items()], ts)
    strata_yield = {"overall": sy["overall"], "per_stratum": {" × ".join(k): {"rate": v[0], "n": v[1]} for k, v in sorted(sy["per_stratum"].items())},
                    "review_trigger": [" × ".join(k) for k in sy["review_trigger"]], "factor": float(ts["stratum_yield_review_factor"])}
    groups: dict[tuple, list[RaceScore]] = defaultdict(list)
    for s in with_q7_scores:
        groups[stratum(s.race_id)].append(s)
    strata_headline = {" × ".join(k): dict(score_set(v).as_dict()) for k, v in sorted(groups.items())}

    return ReleaseEvaluation(version, date, SPEC_VERSION, producer_version, extractor_versions, ts_versions, heldout,
                             [d1, d2, d3, d4, d5, d6], dict(hw.as_dict(), races=[s.race_id for s in with_q7_scores]),
                             dict(hwo.as_dict(), races=without_q7), strata_yield, strata_headline, notes)


def _f(x) -> str:
    return "—" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def render_markdown(ev: ReleaseEvaluation) -> str:
    versions = (f"producer_version: `{ev.producer_version or 'all'}`; extractor_version(s): "
                f"{', '.join(f'`{v}`' for v in ev.extractor_versions) or '—'}; threshold_set_version(s): "
                f"{', '.join(f'`{v}`' for v in ev.threshold_set_versions) or '—'}; held-out races: {len(ev.heldout_ids)}.")
    L = [f"# Release evaluation {ev.version} — SPEC-{ev.spec_version} DoD-1…6 ({ev.date})", "", versions, "",
         f"**v1 Definition of Done: {'COMPLETE' if ev.complete else 'NOT complete'}** (every line must be `pass`; `invalid` is never a pass, §6.3).", "",
         "| ID | Status | Result |", "|---|---|---|"]
    L += [f"| {d.id} | **{d.status}** | {d.summary} |" for d in ev.dods]
    L += ["", "## Headline (§6.2, D-27 weights) — reported with and without Q-7 failures (D-35)", "",
          "| Set | n races | uncovered-outside IoU | covered IoU | rest macro | headline |", "|---|---|---|---|---|---|"]
    for name, h in (("with Q-7 failures (Q-1…Q-6 pass)", ev.headline_with_q7), ("without Q-7 failures (chartable)", ev.headline_without_q7)):
        L.append(f"| {name} | {h['n_races']} | {_f(h['uncovered_outside_iou'])} | {_f(h['covered_iou'])} | {_f(h['rest_macro'])} | {_f(h['headline'])} |")
    trigger = (f"overall chartable rate {_f(ev.strata_yield['overall'])}; review trigger = rate < {ev.strata_yield['factor']} × overall: "
               f"{', '.join(ev.strata_yield['review_trigger']) or 'none'}")
    L += ["", "## Per-stratum yield (D-35) — day/night × field band × start_format × piste", "", trigger, "",
          "| stratum | n | chartable rate |", "|---|---|---|"]
    L += [f"| {k} | {v['n']} | {_f(v['rate'])} |" for k, v in ev.strata_yield["per_stratum"].items()]
    L += ["", "## Per-stratum headline (held-out, Q-1…Q-6 pass)", "", "| stratum | n | uncovered-outside IoU | covered IoU | rest macro | headline |", "|---|---|---|---|---|---|"]
    L += [f"| {k} | {v['n_races']} | {_f(v['uncovered_outside_iou'])} | {_f(v['covered_iou'])} | {_f(v['rest_macro'])} | {_f(v['headline'])} |" for k, v in ev.strata_headline.items()]
    if ev.notes:
        L += ["", "## Notes", ""] + [f"- {n}" for n in ev.notes]
    L += ["", "## Changelog row draft (§14: every held-out evaluation appends an entry)", "", changelog_row(ev), ""]
    return "\n".join(L)


def changelog_row(ev: ReleaseEvaluation) -> str:
    hw, hwo = ev.headline_with_q7, ev.headline_without_q7
    parts = "; ".join(f"{d.id} {d.status}" for d in ev.dods)
    return (f"| {ev.spec_version} | {ev.date} | Release evaluation {ev.version} (`extractor_version` {', '.join(ev.extractor_versions) or '—'}, "
            f"`threshold_set_version` {', '.join(ev.threshold_set_versions) or '—'}): headline {_f(hw['headline'])} with Q-7 failures "
            f"(n={hw['n_races']}) / {_f(hwo['headline'])} without (n={hwo['n_races']}); {parts}. "
            f"v1 {'complete' if ev.complete else 'NOT complete'}. |")
