"""Numpy logistic regression (IRLS with ridge) and metrics; no scikit-learn dependency."""
from __future__ import annotations

import math

import numpy as np


class LogisticRegression:
    def __init__(self, l2: float = 1.0, max_iter: int = 50, tol: float = 1e-8):
        self.l2, self.max_iter, self.tol = l2, max_iter, tol
        self.coef_: np.ndarray | None = None
        self.se_: np.ndarray | None = None
        self.names: list[str] = []
        self.mu_: np.ndarray | None = None
        self.sd_: np.ndarray | None = None

    def _design(self, X: np.ndarray) -> np.ndarray:
        Z = (X - self.mu_) / self.sd_
        return np.hstack([np.ones((len(Z), 1)), Z])

    def fit(self, X: np.ndarray, y: np.ndarray, names: list[str] | None = None) -> LogisticRegression:
        X = np.asarray(X, float); y = np.asarray(y, float)
        self.names = names or [f"x{i}" for i in range(X.shape[1])]
        self.mu_ = X.mean(axis=0); self.sd_ = X.std(axis=0); self.sd_[self.sd_ < 1e-12] = 1.0
        A = self._design(X)
        w = np.zeros(A.shape[1])
        R = np.eye(A.shape[1]) * self.l2; R[0, 0] = 0.0
        for _ in range(self.max_iter):
            p = 1.0 / (1.0 + np.exp(-(A @ w)))
            g = A.T @ (p - y) + R @ w
            H = (A * (p * (1 - p))[:, None]).T @ A + R
            step = np.linalg.solve(H, g)
            w = w - step
            if np.abs(step).max() < self.tol:
                break
        p = 1.0 / (1.0 + np.exp(-(A @ w)))
        H = (A * (p * (1 - p))[:, None]).T @ A + R
        cov = np.linalg.inv(H)
        self.coef_, self.se_ = w, np.sqrt(np.diag(cov))
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-(self._design(np.asarray(X, float)) @ self.coef_)))

    def summary(self) -> dict[str, dict]:
        return {n: {"coef": float(c), "se": float(s), "z": float(c / s) if s > 0 else float("nan")}
                for n, c, s in zip(["intercept", *self.names], self.coef_, self.se_)}


def log_loss(y, p) -> float:
    y = np.asarray(y, float); p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(y, p) -> float:
    return float(np.mean((np.asarray(y, float) - np.asarray(p, float)) ** 2))


def auc(y, p) -> float:
    y = np.asarray(y); p = np.asarray(p)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(p)
    ranks = np.empty(len(p)); ranks[order] = np.arange(1, len(p) + 1)
    # average ranks for ties
    for v in np.unique(p):
        m = p == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    return float((ranks[y == 1].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))
