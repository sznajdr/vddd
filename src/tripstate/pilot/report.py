"""Aggregate pilot race reports into kill-gate measurements and write registers/kill_gates.yaml."""
from __future__ import annotations

import statistics as st
from pathlib import Path

import yaml


def aggregate(reports: list[dict], seeding_minutes: list[float] | None = None, anchor_residuals: dict[str, list[float]] | None = None,
              provisional_tol: dict[str, float] | None = None) -> dict:
    out: dict = {}
    sm = seeding_minutes or [r["seeding_seconds_initial"] / 60 for r in reports if r.get("seeding_seconds_initial") is not None]
    out["KG-1"] = {"measured": st.median(sm) if sm else None, "n": len(sm)}
    ta = [(r["tier_agreement"], r["tier_agreement_n"]) for r in reports if r.get("tier_agreement") is not None]
    out["KG-2"] = {"measured": (sum(a * n for a, n in ta) / sum(n for _, n in ta)) if ta else None, "n": sum(n for _, n in ta)}
    ch = [r["chartable"] for r in reports if r.get("chartable") is not None]
    out["KG-3"] = {"measured": (sum(ch) / len(ch)) if ch else None, "n": len(ch)}
    kg4 = {}
    for stype, res in (anchor_residuals or {}).items():
        if len(res) >= 2:
            off = st.median(res)
            spread = max(abs(x - off) for x in res)
            tol = (provisional_tol or {}).get(stype, 2.0)
            kg4[stype] = {"spread": spread, "tolerance": tol, "ratio": spread / tol if tol else None}
    out["KG-4"] = {"measured": max((v["ratio"] for v in kg4.values()), default=None), "by_start_type": kg4}
    hm = [r["human_minutes"] for r in reports if r.get("human_minutes") is not None]
    out["human_minutes"] = {"median": st.median(hm) if hm else None, "p90": (sorted(hm)[int(0.9 * (len(hm) - 1))] if hm else None), "n": len(hm)}
    out["tracker"] = {p: {"idf1_mean": st.mean([r["tracker"]["idf1"] for r in reports if r["path"] == p and r.get("tracker", {}).get("idf1") is not None] or [float("nan")]),
                          "idsw_total": sum(r["tracker"].get("idsw", 0) for r in reports if r["path"] == p and r.get("tracker"))}
                      for p in sorted({r["path"] for r in reports})}
    out["flags_per_race"] = {p: st.mean([len(r["flags"]) for r in reports if r["path"] == p] or [0]) for p in sorted({r["path"] for r in reports})}
    return out


def evaluate_kill_gates(agg: dict) -> dict[str, str]:
    status = {}
    m1 = agg["KG-1"]["measured"]; status["KG-1"] = "not_evaluated" if m1 is None else ("fail" if m1 > 8 else "pass")
    m2 = agg["KG-2"]["measured"]; status["KG-2"] = "not_evaluated" if m2 is None else ("recalibrate_once" if m2 < 0.85 else "pass")
    m3 = agg["KG-3"]["measured"]; status["KG-3"] = "not_evaluated" if m3 is None else ("fail" if m3 < 0.40 else "pass")
    m4 = agg["KG-4"]["measured"]; status["KG-4"] = "not_evaluated" if m4 is None else ("fail" if m4 > 2.0 else "pass")
    return status


def write_kill_gates(path: Path, agg: dict, evidence: str) -> dict:
    reg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    status = evaluate_kill_gates(agg)
    for g in reg["gates"]:
        if g["id"] in status and status[g["id"]] != "not_evaluated":
            g["status"] = status[g["id"]]
            g["measured"] = agg[g["id"]]["measured"]
            g["evidence"] = evidence
    Path(path).write_text(yaml.safe_dump(reg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return status


def markdown(agg: dict, status: dict[str, str]) -> str:
    lines = ["# Pilot report (throwaway stack; producer_kind = pilot_throwaway)", "",
             "| Gate | Measured | n | Status |", "|---|---|---|---|"]
    for k in ("KG-1", "KG-2", "KG-3", "KG-4"):
        m = agg[k]["measured"]
        lines.append(f"| {k} | {'—' if m is None else round(m, 3)} | {agg[k].get('n', '')} | {status[k]} |")
    hm = agg["human_minutes"]
    lines += ["", f"Human-minutes: median {hm['median']}, p90 {hm['p90']} (n={hm['n']}) → `dod3_median_target_min` / `human_budget_cap_min` instantiation inputs (D-29).", "",
              "| Path | IDF1 (mean) | ID switches | flags / race |", "|---|---|---|---|"]
    for p, v in agg["tracker"].items():
        lines.append(f"| {p} | {round(v['idf1_mean'], 3)} | {v['idsw_total']} | {round(agg['flags_per_race'][p], 1)} |")
    return "\n".join(lines) + "\n"
