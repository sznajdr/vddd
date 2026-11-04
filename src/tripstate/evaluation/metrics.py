"""§6.2 metrics (2.0.0: L-29…L-32; D-27, D-28, D-31) plus descriptive action-segmentation metrics (RP-14).

Segments are dicts with at least: saddle_no, state_kind, state, covered, t_start_frac, t_end_frac,
tier_attr. Intervals are half-open [a, b) in race fraction. The evaluation mask per runner is the
time where the hand chart marks the runner observable AND the configured shot type is present;
predicted NOT_VISIBLE/UNKNOWN stay inside the mask and therefore count as misses.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

Interval = tuple[float, float]
REST_STATES = ("LEADER", "RAIL_UNCOVERED", "WIDE")  # D-28: DETACHED removed from rest


def _norm(ivs: Iterable[Interval]) -> list[Interval]:
    s = sorted((a, b) for a, b in ivs if b > a)
    out: list[Interval] = []
    for a, b in s:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def intersect(x: Iterable[Interval], y: Iterable[Interval]) -> list[Interval]:
    X, Y = _norm(x), _norm(y)
    out = []
    i = j = 0
    while i < len(X) and j < len(Y):
        a, b = max(X[i][0], Y[j][0]), min(X[i][1], Y[j][1])
        if b > a:
            out.append((a, b))
        if X[i][1] < Y[j][1]:
            i += 1
        else:
            j += 1
    return out


def length(ivs: Iterable[Interval]) -> float:
    return sum(b - a for a, b in _norm(ivs))


def _ivs(rows: Iterable[dict], pred) -> list[Interval]:
    return [(r["t_start_frac"], r["t_end_frac"]) for r in rows if pred(r)]


def segment_iou(pred: Iterable[Interval], true: Iterable[Interval], mask: Iterable[Interval]) -> float | None:
    """IoU over the mask; None when the union inside the mask is empty (omitted, never scored 1)."""
    p, t = intersect(pred, mask), intersect(true, mask)
    union = length(_norm(p + t))
    if union <= 0:
        return None
    return length(intersect(p, t)) / union


def per_runner_state_iou(pred_rows: Sequence[dict], true_rows: Sequence[dict], mask: Iterable[Interval], state: str) -> float | None:
    is_state = lambda r: r["state_kind"] == "base" and r["state"] == state
    return segment_iou(_ivs(pred_rows, is_state), _ivs(true_rows, is_state), mask)


def macro_iou(per_state: dict[str, float | None]) -> float | None:
    vals = [v for v in per_state.values() if v is not None]
    return sum(vals) / len(vals) if vals else None


def is_covered(r: dict) -> bool:
    return r["state_kind"] == "base" and r.get("covered") is True


def is_uncovered_outside(r: dict) -> bool:
    """D-27 money mask: tier >= 2 and not covered. PARKED is tier 2 uncovered by definition; WIDE carries tier_attr."""
    if r["state_kind"] != "base":
        return False
    if r["state"] == "PARKED":
        return True
    return r["state"] == "WIDE" and r.get("covered") is False


def mask_iou(pred_rows: Sequence[dict], true_rows: Sequence[dict], mask: Iterable[Interval], predicate) -> float | None:
    return segment_iou(_ivs(pred_rows, predicate), _ivs(true_rows, predicate), mask)


def headline_score(uncovered_outside_iou: float | None, covered_iou: float | None, rest_macro: float | None,
                   weights: tuple[float, float, float] = (0.5, 0.3, 0.2)) -> float | None:
    """0.5·IoU(uncovered-outside mask) + 0.3·IoU(covered mask) + 0.2·MacroIoU(rest). None if a DoD-1 component is undefined."""
    if uncovered_outside_iou is None or covered_iou is None:
        return None
    rest = rest_macro if rest_macro is not None else 0.0
    w = weights
    return w[0] * uncovered_outside_iou + w[1] * covered_iou + w[2] * rest


def wilson_ci(k: int, n: int, z: float = 1.959964) -> tuple[float, float, float]:
    """(point, lo, hi) Wilson score interval for k successes in n trials (D-31)."""
    if n <= 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (p, max(0.0, centre - half), min(1.0, centre + half))


def break_candidate_recall(cand_starts_s: Sequence[float], truth_starts_s: Sequence[float], tol_s: float) -> tuple[int, int, list[tuple[int, int]]]:
    """One-to-one minimum-time-distance matching within tol_s (§6.2). Returns (matched, n_truth, pairs)."""
    pairs = sorted(
        ((abs(c - t), ci, ti) for ci, c in enumerate(cand_starts_s) for ti, t in enumerate(truth_starts_s) if abs(c - t) <= tol_s),
        key=lambda x: (x[0], x[2], x[1]),
    )
    used_c: set[int] = set()
    used_t: set[int] = set()
    matched: list[tuple[int, int]] = []
    for _, ci, ti in pairs:
        if ci in used_c or ti in used_t:
            continue
        used_c.add(ci)
        used_t.add(ti)
        matched.append((ci, ti))
    return len(matched), len(truth_starts_s), matched


# --- Descriptive action-segmentation metrics (RP-14; Lea et al. 2017 conventions) ---

def _labels_seq(rows: Sequence[dict]) -> list[str]:
    seq = [r["state"] for r in sorted((r for r in rows if r["state_kind"] == "base"), key=lambda r: r["t_start_frac"])]
    out: list[str] = []
    for s in seq:
        if not out or out[-1] != s:
            out.append(s)
    return out


def edit_score(pred_rows: Sequence[dict], true_rows: Sequence[dict]) -> float:
    """Segmental edit score in [0, 100]: 1 - Levenshtein(pred labels, true labels) / max(len)."""
    p, t = _labels_seq(pred_rows), _labels_seq(true_rows)
    if not p and not t:
        return 100.0
    d = [[0] * (len(t) + 1) for _ in range(len(p) + 1)]
    for i in range(len(p) + 1):
        d[i][0] = i
    for j in range(len(t) + 1):
        d[0][j] = j
    for i in range(1, len(p) + 1):
        for j in range(1, len(t) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (p[i - 1] != t[j - 1]))
    return 100.0 * (1 - d[len(p)][len(t)] / max(len(p), len(t)))


def f1_at_k(pred_rows: Sequence[dict], true_rows: Sequence[dict], k: float) -> float:
    """Segmental F1@k: a predicted base segment is a TP if an unmatched true segment with the same
    label overlaps it with IoU >= k; else FP. Unmatched true segments are FN."""
    P = [r for r in pred_rows if r["state_kind"] == "base"]
    T = [r for r in true_rows if r["state_kind"] == "base"]
    used = [False] * len(T)
    tp = fp = 0
    for p in P:
        best, bi = 0.0, -1
        for i, t in enumerate(T):
            if used[i] or t["state"] != p["state"]:
                continue
            inter = max(0.0, min(p["t_end_frac"], t["t_end_frac"]) - max(p["t_start_frac"], t["t_start_frac"]))
            union = (p["t_end_frac"] - p["t_start_frac"]) + (t["t_end_frac"] - t["t_start_frac"]) - inter
            iou = inter / union if union > 0 else 0.0
            if iou > best:
                best, bi = iou, i
        if bi >= 0 and best >= k:
            used[bi] = True
            tp += 1
        else:
            fp += 1
    fn = used.count(False)
    if tp == 0:
        return 0.0
    prec, rec = tp / (tp + fp), tp / (tp + fn)
    return 2 * prec * rec / (prec + rec)
