import numpy as np

from tripstate.signal import (
    LogisticRegression,
    auc,
    build_features,
    log_loss,
    run_gate,
    synthetic_corpus,
)
from tripstate.signal.corpus import RunnerRow


def test_logistic_regression_recovers_coefficients():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(4000, 2))
    p = 1 / (1 + np.exp(-(0.5 + 1.2 * X[:, 0] - 0.8 * X[:, 1])))
    y = (rng.random(4000) < p).astype(float)
    m = LogisticRegression(l2=0.01).fit(X, y, ["a", "b"])
    s = m.summary()
    assert abs(s["a"]["coef"] - 1.2) < 0.15 and abs(s["b"]["coef"] + 0.8) < 0.15 and s["a"]["z"] > 10
    assert auc(y, m.predict_proba(X)) > 0.75 and log_loss(y, m.predict_proba(X)) < log_loss(y, np.full(4000, y.mean()))


def test_features_use_only_strictly_earlier_races():
    rows = synthetic_corpus(n_horses=30, n_races=60, seed=1)
    X, _y, _rids, _dates = build_features(rows, k_prior=3)
    # first appearance of each horse has no prior
    seen = set()
    for r, f in zip(rows, X):
        if r.horse_id not in seen:
            assert f["n_prior"] == 0 and f["parked_any"] == 0
            seen.add(r.horse_id)
    # changing a row's OWN notule must not change its features (same-race text is never a feature)
    i = next(k for k, r in enumerate(rows) if X[k]["n_prior"] > 0)
    rows2 = list(rows); r = rows2[i]
    rows2[i] = RunnerRow(r.race_id, r.date, r.horse_id, r.saddle_no, r.finish_position, r.win, r.placed, r.odds, "nez au vent en deuxième épaisseur")
    X2, *_ = build_features(rows2, k_prior=3)
    assert X2[i] == X[i]


def test_gate_detects_injected_signal_and_rejects_none():
    go = run_gate(synthetic_corpus(n_horses=150, n_races=1200, trip_effect=1.2, seed=2), {"bootstrap": 60})
    assert go["verdict"] == "go", go["reasons"]
    assert go["indicators"]["parked_last"]["sign"] > 0 or go["indicators"]["parked_any"]["sign"] > 0
    for seed in (3, 5, 7):
        nogo = run_gate(synthetic_corpus(n_horses=150, n_races=900, trip_effect=0.0, seed=seed), {"bootstrap": 60})
        assert nogo["verdict"] == "no-go", (seed, nogo["reasons"])


def test_gate_inconclusive_on_small_corpus():
    r = run_gate(synthetic_corpus(n_horses=20, n_races=40, seed=4))
    assert r["verdict"] == "inconclusive" and "rows" in r["reasons"][0]
