"""Pre-registered signal-gate evaluation (protocols/SIGNAL-GATE/decision.yaml)."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

from tripstate.signal.corpus import RunnerRow
from tripstate.signal.features import build_features
from tripstate.signal.model import LogisticRegression, auc, brier, log_loss

DEFAULT_DECISION = {
    "k_prior": 3, "holdout_months": 12, "min_rows": 2000, "min_holdout_wins": 50,
    "min_logloss_gain_nats": 0.002, "min_coef_z": 2.7, "min_stable_folds": 3, "min_ablation_gain_nats": 0.0005, "n_folds": 3, "l2": 1.0,
    "bootstrap": 200, "seed": 0,
    "indicator_features": ["parked_any", "parked_last", "covered_any", "leader_any", "wide_any", "break_any", "detached_any"],
}


def _matrix(X: list[dict], names: list[str]) -> np.ndarray:
    return np.array([[float(x[n]) for n in names] for x in X])


def _months_before(date: str, months: int) -> str:
    y, m, d = int(date[:4]), int(date[5:7]), int(date[8:10])
    m -= months
    while m <= 0:
        m += 12; y -= 1
    return f"{y:04d}-{m:02d}-{d:02d}"


def _race_bootstrap_gain(y, p_base, p_full, rids, n_boot: int, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    y = np.asarray(y); p_base = np.asarray(p_base); p_full = np.asarray(p_full)
    groups: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rids):
        groups[r].append(i)
    keys = list(groups)
    gains = []
    for _ in range(n_boot):
        pick = rng.choice(len(keys), len(keys), replace=True)
        idx = np.concatenate([groups[keys[k]] for k in pick])
        gains.append(log_loss(y[idx], p_base[idx]) - log_loss(y[idx], p_full[idx]))
    return float(np.percentile(gains, 2.5)), float(np.percentile(gains, 97.5))


def run_gate(rows: list[RunnerRow], decision: dict | None = None) -> dict:
    cfg = dict(DEFAULT_DECISION, **(decision or {}))
    X, y, rids, dates = build_features(rows, cfg["k_prior"])
    feats = cfg["indicator_features"]
    base_names, full_names = ["market_logit"], ["market_logit", *feats]
    n = len(rows)
    report: dict = {"n_rows": n, "n_races": len(set(rids)), "decision": cfg, "verdict": "inconclusive", "reasons": []}
    if n < cfg["min_rows"]:
        report["reasons"].append(f"only {n} rows (< {cfg['min_rows']})")
        return report
    last = max(dates)
    cut = _months_before(last, cfg["holdout_months"])
    tr = [i for i, d in enumerate(dates) if d < cut]
    te = [i for i, d in enumerate(dates) if d >= cut]
    ytr, yte = np.array([y[i] for i in tr]), np.array([y[i] for i in te])
    if len(tr) == 0:
        report["reasons"].append(f"no rows before the holdout cutoff {cut} (corpus spans less than {cfg['holdout_months']} months)")
        return report
    if yte.sum() < cfg["min_holdout_wins"]:
        report["reasons"].append(f"holdout has {int(yte.sum())} wins (< {cfg['min_holdout_wins']})")
        return report
    Xtr, Xte = [X[i] for i in tr], [X[i] for i in te]
    base = LogisticRegression(cfg["l2"]).fit(_matrix(Xtr, base_names), ytr, base_names)
    full = LogisticRegression(cfg["l2"]).fit(_matrix(Xtr, full_names), ytr, full_names)
    pb, pf = base.predict_proba(_matrix(Xte, base_names)), full.predict_proba(_matrix(Xte, full_names))
    gain = log_loss(yte, pb) - log_loss(yte, pf)
    lo, hi = _race_bootstrap_gain(yte, pb, pf, [rids[i] for i in te], cfg["bootstrap"], cfg["seed"])
    report["holdout"] = {"cutoff": cut, "n": len(te), "wins": int(yte.sum()),
                         "baseline": {"log_loss": log_loss(yte, pb), "brier": brier(yte, pb), "auc": auc(yte, pb)},
                         "full": {"log_loss": log_loss(yte, pf), "brier": brier(yte, pf), "auc": auc(yte, pf)},
                         "logloss_gain": gain, "gain_ci95": [lo, hi]}
    report["coefficients_holdout_fit"] = full.summary()
    # yearly-ish rolling folds for sign stability
    n_folds = cfg["n_folds"]
    tr_dates = sorted({dates[i] for i in tr})
    bounds = [tr_dates[int(len(tr_dates) * (j + 1) / n_folds) - 1] for j in range(n_folds)]
    folds = []
    prev = ""
    for j, b in enumerate(bounds):
        idx = [i for i in tr if prev < dates[i] <= b]
        prev = b
        if sum(y[i] for i in idx) < 20:
            continue
        m = LogisticRegression(cfg["l2"]).fit(_matrix([X[i] for i in idx], full_names), np.array([y[i] for i in idx]), full_names)
        folds.append({"fold": j, "n": len(idx), "coef": {k: v["coef"] for k, v in m.summary().items()}})
    report["folds"] = folds
    stable = {}
    for f in feats:
        signs = [np.sign(fd["coef"][f]) for fd in folds if abs(fd["coef"][f]) > 1e-9]
        z = report["coefficients_holdout_fit"][f]["z"]
        n_same = max(signs.count(1.0), signs.count(-1.0)) if signs else 0
        stable[f] = {"z": z, "stable_folds": n_same, "sign": float(np.sign(report["coefficients_holdout_fit"][f]["coef"]))}
    report["indicators"] = stable
    gain_ok = gain >= cfg["min_logloss_gain_nats"] and lo > 0
    # coefficient route: significant and sign-stable AND removing the indicator worsens holdout log-loss (ablation)
    coef_ok = []
    for f, s in stable.items():
        if abs(s["z"]) < cfg["min_coef_z"] or s["stable_folds"] < cfg["min_stable_folds"]:
            continue
        names_wo = [n for n in full_names if n != f]
        m_wo = LogisticRegression(cfg["l2"]).fit(_matrix(Xtr, names_wo), ytr, names_wo)
        abl = log_loss(yte, m_wo.predict_proba(_matrix(Xte, names_wo))) - log_loss(yte, pf)
        stable[f]["ablation_gain"] = abl
        if abl >= cfg["min_ablation_gain_nats"]:
            coef_ok.append(f)
    if gain_ok or coef_ok:
        report["verdict"] = "go"
        report["reasons"].append(f"log-loss gain {gain:.4f} nats, CI [{lo:.4f}, {hi:.4f}]" if gain_ok else "no significant log-loss gain")
        if coef_ok:
            report["reasons"].append("stable significant indicators: " + ", ".join(coef_ok))
    else:
        report["verdict"] = "no-go"
        report["reasons"].append(f"log-loss gain {gain:.4f} nats (CI [{lo:.4f}, {hi:.4f}]) below {cfg['min_logloss_gain_nats']:.4f} "
                                 f"and no indicator with |z| ≥ {cfg['min_coef_z']:.1f}, sign-stable across ≥ {cfg['min_stable_folds']} folds "
                                 f"and holdout ablation gain ≥ {cfg['min_ablation_gain_nats']:.4f}")
    return report


def markdown(report: dict) -> str:
    lines = ["# Signal gate report", "", f"Rows: {report['n_rows']}, races: {report['n_races']}. **Verdict: {report['verdict'].upper()}**", ""]
    for r in report["reasons"]:
        lines.append(f"- {r}")
    h = report.get("holdout")
    if h:
        lines += ["", f"Holdout from {h['cutoff']} (n={h['n']}, wins={h['wins']})", "", "| model | log-loss | Brier | AUC |", "|---|---|---|---|"]
        for k in ("baseline", "full"):
            m = h[k]; lines.append(f"| {k} | {m['log_loss']:.4f} | {m['brier']:.4f} | {m['auc']:.3f} |")
        lines += ["", f"Log-loss gain: {h['logloss_gain']:.4f} nats, race-bootstrap 95% CI [{h['gain_ci95'][0]:.4f}, {h['gain_ci95'][1]:.4f}]", "",
                  "| indicator | coef | z | sign-stable folds | holdout ablation gain |", "|---|---|---|---|---|"]
        for f, s in report["indicators"].items():
            c = report["coefficients_holdout_fit"][f]
            abl = s.get("ablation_gain")
            lines.append(f"| {f} | {c['coef']:+.3f} | {s['z']:+.2f} | {s['stable_folds']}/{len(report['folds'])} | {'—' if abl is None else f'{abl:+.4f}'} |")
    return "\n".join(lines) + "\n"
