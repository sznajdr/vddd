"""Tracker quality against the operator-corrected result: IDF1, ID switches, MOTA-lite (research 07).
Hungarian assignment implemented locally (no scipy)."""
from __future__ import annotations

import numpy as np

from tripstate.pilot.track import iou


def hungarian_max(score: np.ndarray) -> list[tuple[int, int]]:
    """Maximum-weight assignment on a rectangular matrix (rows ≤ cols padded internally). O(n³)."""
    s = np.asarray(score, dtype=float)
    n, m = s.shape
    k = max(n, m)
    cost = np.zeros((k, k))
    cost[:n, :m] = -s
    # classic potentials-based Hungarian (1-indexed arrays)
    u = np.zeros(k + 1); v = np.zeros(k + 1); p = np.zeros(k + 1, dtype=int); way = np.zeros(k + 1, dtype=int)
    for i in range(1, k + 1):
        p[0] = i; j0 = 0
        minv = np.full(k + 1, np.inf); used = np.zeros(k + 1, dtype=bool)
        while True:
            used[j0] = True; i0 = p[j0]; delta = np.inf; j1 = 0
            for j in range(1, k + 1):
                if not used[j]:
                    cur = cost[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur; way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]; j1 = j
            for j in range(k + 1):
                if used[j]:
                    u[p[j]] += delta; v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
            if j0 == 0:
                break
    pairs = []
    for j in range(1, k + 1):
        i = p[j]
        if 1 <= i <= n and 1 <= j <= m and s[i - 1, j - 1] > 0:
            pairs.append((i - 1, j - 1))
    return pairs


def frame_matches(pred: dict[int, object], truth: dict[int, object], thr: float) -> list[tuple[int, int]]:
    """Per-frame matching (pred id, truth id) maximizing IoU sum above thr."""
    pids, tids = sorted(pred), sorted(truth)
    if not pids or not tids:
        return []
    m = np.zeros((len(pids), len(tids)))
    for i, pi in enumerate(pids):
        for j, tj in enumerate(tids):
            v = iou(pred[pi], truth[tj])
            m[i, j] = v if v >= thr else 0.0
    return [(pids[i], tids[j]) for i, j in hungarian_max(m)]


def idf1(pred_tl: dict[int, dict[int, object]], truth_tl: dict[int, dict[int, object]], thr: float = 0.5) -> dict:
    """IDF1 over identities: global overlap counts -> Hungarian -> IDTP."""
    pids = sorted({p for d in pred_tl.values() for p in d}); tids = sorted({t for d in truth_tl.values() for t in d})
    overlap = np.zeros((len(pids), len(tids)))
    pi = {p: i for i, p in enumerate(pids)}; ti = {t: j for j, t in enumerate(tids)}
    for f, truth in truth_tl.items():
        for p, t in frame_matches(pred_tl.get(f, {}), truth, thr):
            overlap[pi[p], ti[t]] += 1
    idtp = sum(overlap[i, j] for i, j in hungarian_max(overlap)) if overlap.size else 0.0
    n_pred = sum(len(d) for d in pred_tl.values()); n_true = sum(len(d) for d in truth_tl.values())
    idfp, idfn = n_pred - idtp, n_true - idtp
    return {"idf1": (2 * idtp / (2 * idtp + idfp + idfn)) if (idtp + idfp + idfn) else None, "idtp": idtp, "idfp": idfp, "idfn": idfn}


def id_switches(pred_tl: dict[int, dict[int, object]], truth_tl: dict[int, dict[int, object]], thr: float = 0.5) -> int:
    """Count of times a truth identity's matched predicted id changes (classic IDSW)."""
    last: dict[int, int] = {}
    sw = 0
    for f in sorted(truth_tl):
        for p, t in frame_matches(pred_tl.get(f, {}), truth_tl[f], thr):
            if t in last and last[t] != p:
                sw += 1
            last[t] = p
    return sw


def mota_lite(pred_tl, truth_tl, thr: float = 0.5) -> dict:
    fp = fn = 0
    for f in sorted(truth_tl):
        m = frame_matches(pred_tl.get(f, {}), truth_tl[f], thr)
        fn += len(truth_tl[f]) - len(m); fp += len(pred_tl.get(f, {})) - len(m)
    sw = id_switches(pred_tl, truth_tl, thr)
    n_true = sum(len(d) for d in truth_tl.values())
    return {"mota": 1 - (fp + fn + sw) / n_true if n_true else None, "fp": fp, "fn": fn, "idsw": sw}
