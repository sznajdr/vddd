"""Lateral tiering and cover (SPEC-2.0.0-draft §2.2 as amended by L-10/L-11; D-26; EC-13).

All inputs are already in pack-space units (SL longitudinal, SW lateral). No pixels here.
Deterministic: ties broken by saddle_no, never by input order.
"""
from __future__ import annotations

from collections.abc import Sequence
from statistics import median

from tripstate.config import ThresholdSet


def _median(xs: Sequence[float]) -> float:
    return float(median(xs))


def split_by_span(sorted_w: list[float], max_span: float) -> list[list[float]]:
    """Recursively split a rail-outward-sorted cluster whose span exceeds max_span at its
    largest internal gap. Ties -> the lower-index gap. Deterministic (L-10)."""
    if len(sorted_w) < 2 or (sorted_w[-1] - sorted_w[0]) <= max_span:
        return [sorted_w]
    gaps = [sorted_w[i + 1] - sorted_w[i] for i in range(len(sorted_w) - 1)]
    cut = gaps.index(max(gaps))  # first occurrence = lower index on ties
    left, right = sorted_w[: cut + 1], sorted_w[cut + 1 :]
    return split_by_span(left, max_span) + split_by_span(right, max_span)


def cluster_tiers(
    w_sw: Sequence[float],
    saddle_nos: Sequence[int],
    ts: ThresholdSet,
) -> dict[int, int]:
    """Occupied lateral clusters, 1 = innermost (closest to rail), per §2.2 median-linkage:
    sort rail-outward by (w_sw, saddle_no); first runner starts cluster 1; each next runner
    joins the current cluster iff |w - current median| < same_tier_sw (strict), else starts
    the next; the median is recomputed after each assignment. Then any cluster with span
    > max_tier_span_sw is split at its largest internal gap (L-10).

    Returns {saddle_no: cluster_id}. Only valid runners should be passed.
    """
    if len(w_sw) != len(saddle_nos):
        raise ValueError("w_sw and saddle_nos length mismatch")
    if not w_sw:
        return {}
    same_tier = float(ts["same_tier_sw"])
    max_span = float(ts["max_tier_span_sw"])

    order = sorted(range(len(w_sw)), key=lambda i: (w_sw[i], saddle_nos[i]))
    clusters: list[list[int]] = [[order[0]]]
    cur_vals: list[float] = [w_sw[order[0]]]
    for i in order[1:]:
        if abs(w_sw[i] - _median(cur_vals)) < same_tier:
            clusters[-1].append(i)
            cur_vals.append(w_sw[i])
        else:
            clusters.append([i])
            cur_vals = [w_sw[i]]

    # Span bound: split clusters by value, then re-map indices (values are sorted within cluster).
    bounded: list[list[int]] = []
    for members in clusters:
        vals = [w_sw[i] for i in members]
        parts = split_by_span(vals, max_span)
        pos = 0
        for part in parts:
            bounded.append(members[pos : pos + len(part)])
            pos += len(part)

    out: dict[int, int] = {}
    for cid, members in enumerate(bounded, start=1):
        for i in members:
            out[saddle_nos[i]] = cid
    return out


def absolute_tiers(
    clusters: dict[int, int],
    w_sw_by_saddle: dict[int, float],
    rail_ref_w_sw: float | None,
    rail_ref_conf: float | None,
    ts: ThresholdSet,
) -> dict[int, int | None]:
    """Attach occupied cluster 1 to absolute tier 1 only when the rail reference is valid and
    cluster 1's median center is within rail_attach_sw of rail_ref_w_sw + rail_lane_center_offset_sw.
    Otherwise every absolute tier is None (EC-13: never promote the innermost occupied cluster).
    """
    if not clusters:
        return {}
    conf_min = float(ts.get("rail_ref_conf_min", 0.5))
    if rail_ref_w_sw is None or rail_ref_conf is None or rail_ref_conf < conf_min:
        return {s: None for s in clusters}
    expected = rail_ref_w_sw + float(ts["rail_lane_center_offset_sw"])
    c1 = [w_sw_by_saddle[s] for s, c in clusters.items() if c == 1]
    if abs(_median(c1) - expected) > float(ts["rail_attach_sw"]):  # closed boundary
        return {s: None for s in clusters}
    return dict(clusters)


def covered(
    x: int,
    l_sl: dict[int, float],
    w_sw: dict[int, float],
    ts: ThresholdSet,
) -> bool:
    """D-26 cover predicate (L-11): X is covered iff there exists a valid Y with
    (l_Y - l_X) in [cover_min_sl, cover_max_sl] (closed) and |w_X - w_Y| < cover_lat_sw.
    Tier-independent. Dict keys = valid runners only.
    """
    cmin, cmax = float(ts["cover_min_sl"]), float(ts["cover_max_sl"])
    lat = float(ts["cover_lat_sw"])
    lx, wx = l_sl[x], w_sw[x]
    for y, ly in l_sl.items():
        if y == x:
            continue
        d = ly - lx
        if cmin <= d <= cmax and abs(wx - w_sw[y]) < lat:
            return True
    return False


def covered_all(l_sl: dict[int, float], w_sw: dict[int, float], ts: ThresholdSet) -> dict[int, bool]:
    return {x: covered(x, l_sl, w_sw, ts) for x in l_sl}
