"""M3 consistency checks (SPEC-2.0.0-draft §4 M3 DoD; D-23, D-25, D-30, D-34; L-21…L-23; DR-04).

Non-corrective: contradictions set statuses and `id_suspect`, never identities. Identity never comes from
post-hoc finish/start observation (D-01).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import pairwise

from tripstate.config import ThresholdSet


# ---------------------------------------------------------------- EC-12 (D-34)
def anchor_check(video_duration_s: float, official_elapsed_norm_s: float | None, start_type: str, ts: ThresholdSet) -> dict:
    """EC-12 under D-34 (per-start-type offset + tolerance); evidence-gated values until OD-1x."""
    if official_elapsed_norm_s is None:
        return {"anchor_check_status": "inconclusive", "anchor_duration_delta_s": None, "anchor_suspect": False}
    offset = float(ts[f"anchor_offset_{start_type}_s"])
    tol = float(ts[f"anchor_tol_{start_type}_s"])
    delta = video_duration_s - official_elapsed_norm_s
    status = "pass" if abs(delta - offset) <= tol else "mismatch"
    return {"anchor_check_status": status, "anchor_duration_delta_s": delta, "anchor_suspect": status == "mismatch"}


# ---------------------------------------------------------------- crossing reconstruction
def reconstruct_crossings(timeline: dict[int, dict[int, object]], finish_line: tuple[tuple[float, float], tuple[float, float]],
                          fps: float) -> list[tuple[int, float]]:
    """Visibly observed finish crossings from identified boxes: the first frame where a runner's foot point
    changes side of the finish line relative to the side it was first seen on. Returns (saddle, t_video_s)
    sorted by time, interpolated between frames."""
    (x1, y1), (x2, y2) = finish_line
    nx, ny = (y2 - y1), -(x2 - x1)   # line normal
    norm = (nx * nx + ny * ny) ** 0.5 or 1.0
    nx, ny = nx / norm, ny / norm

    def side(b) -> float:
        px, py = (b.x1 + b.x2) / 2.0, max(b.y1, b.y2)
        return (px - x1) * nx + (py - y1) * ny

    first_side: dict[int, float] = {}
    last_val: dict[int, tuple[int, float]] = {}
    out: list[tuple[int, float]] = []
    done: set[int] = set()
    for f in sorted(timeline):
        for s, b in timeline[f].items():
            if s in done:
                continue
            v = side(b)
            if s not in first_side:
                first_side[s] = v
                last_val[s] = (f, v)
                continue
            pf, pv = last_val[s]
            sgn = 1.0 if first_side[s] >= 0 else -1.0
            crossed_now, crossed_before = v * sgn < 0, pv * sgn < 0   # exactly on the line = not yet crossed
            if crossed_now and not crossed_before:
                frac = pv / (pv - v) if (pv - v) != 0 else 0.0
                out.append((s, (pf + frac * (f - pf)) / fps))
                done.add(s)
            last_val[s] = (f, v)
    return sorted(out, key=lambda x: x[1])


# ---------------------------------------------------------------- finish check (D-23 / D-25 / D-30)
@dataclass
class FinishInputs:
    observed_crossings: list[tuple[int, float]]            # identified runners seen crossing, (saddle, t)
    coverage_before_first_crossing: bool
    official_order: list[int]                               # final official order, winner first ([] if unavailable)
    provisional_order: list[int] | None = None              # photo/provisional order if ingested
    arrival_revised: bool | None = None
    revision_implicated: set[int] = field(default_factory=set)   # arrival_revision_type in {retrograde, post_finish_dq, other}
    unknown_status: set[int] = field(default_factory=set)        # arrival_revision_type == unknown
    excluded: set[int] = field(default_factory=set)              # NP / DAI / DQ
    adjudication: str | None = None                         # None | identity_error | arrival_revision
    adjudicated_first_past: int | None = None


@dataclass
class FinishResult:
    finish_check_status: str          # pass | mismatch | inconclusive | pending_adjudication
    finish_check_basis: str
    first_past_saddle_no: int | None
    first_past_method: str | None
    finish_evidence_n: int
    id_suspect: bool
    arrival_revised: bool | None
    needs_adjudication: bool
    notes: list[str] = field(default_factory=list)


def reference_order(inp: FinishInputs) -> tuple[list[int], str]:
    if inp.provisional_order:
        return [s for s in inp.provisional_order if s not in inp.excluded], "provisional"
    if not inp.official_order:
        return [], "unavailable"
    ref = [s for s in inp.official_order if s not in inp.excluded and s not in inp.revision_implicated]
    if inp.arrival_revised is False:
        return ref, "final_unrevised"
    if inp.revision_implicated & set(inp.official_order):
        return ref, "final_revision_carveout"
    if inp.unknown_status & set(ref):
        return ref, "final_assumed"
    return ref, "final_assumed" if inp.arrival_revised is None else "final_unrevised"


def _contradiction(observed: list[int], ref: list[int]) -> bool:
    rank = {s: i for i, s in enumerate(ref)}
    obs = [s for s in observed if s in rank]
    return any(rank[a] > rank[b] for i, a in enumerate(obs) for b in obs[i + 1:])


def finish_check(inp: FinishInputs, finish_evidence_min_k: int) -> FinishResult:
    ref, basis = reference_order(inp)
    observed = [s for s, _ in inp.observed_crossings]
    in_ref = [s for s in observed if s in ref]
    outside = [s for s in observed if s not in ref]
    n_evidence = len(in_ref)
    notes: list[str] = []
    revised_out = inp.arrival_revised
    revision_evidence = bool(inp.revision_implicated) or inp.arrival_revised is True

    # (a) status
    if not ref:
        status = "inconclusive"; notes.append("no reference order")
    elif _contradiction(observed, ref):
        if inp.adjudication == "identity_error":
            status = "mismatch"
        elif inp.adjudication == "arrival_revision":
            status = "inconclusive"; revised_out = True; notes.append("adjudicated: arrival revision")
        elif inp.arrival_revised is False:
            status = "mismatch"; notes.append("contradiction against an authoritative unrevised order")
        else:
            status = "pending_adjudication"
    elif outside:
        status = "inconclusive"; notes.append(f"observed crossers outside the reference: {sorted(set(outside))}")
    elif n_evidence == 0:
        status = "inconclusive"; notes.append("no observed crossing of a reference runner")
    else:
        status = "pass"
    id_suspect = status == "mismatch"
    needs_adj = status == "pending_adjudication"

    # first-past ladder (D-25 with the D-30 evidence bar)
    fp: int | None = None; method: str | None = None
    if inp.coverage_before_first_crossing and inp.observed_crossings:
        fp, method = inp.observed_crossings[0][0], "observed_crossing"
    elif status in ("pass", "inconclusive") and not needs_adj and inp.official_order and not revision_evidence \
            and n_evidence >= finish_evidence_min_k and not _contradiction(observed, ref):
        winner = next((s for s in inp.official_order if s not in inp.excluded), None)
        if winner is not None:
            fp = winner
            method = "official_unrevised" if inp.arrival_revised is False else "official_assumed"
    elif inp.adjudication is not None and inp.adjudicated_first_past is not None:
        fp, method = inp.adjudicated_first_past, "human_confirm"
    if fp is None and status != "pending_adjudication" and n_evidence < finish_evidence_min_k and not (inp.coverage_before_first_crossing and inp.observed_crossings):
        notes.append(f"{n_evidence} observed crossings < finish_evidence_min_k={finish_evidence_min_k}: no adoption (D-30), EC-12 inconclusive")
    return FinishResult(status, basis, fp, method, n_evidence, id_suspect, revised_out, needs_adj, notes)


# ---------------------------------------------------------------- start check (b) incl. DR-04 two rows
@dataclass
class StartResult:
    start_check_status: str       # pass | mismatch | inconclusive
    notes: list[str] = field(default_factory=list)


def start_check_autostart(lineup: dict[int, tuple[float, float]], post_positions: dict[int, int],
                          autostart_rows: dict[int, int] | None = None, field_size: int | None = None) -> StartResult:
    """lineup: visible runners -> (l_sl, w_sw) at the start frame. Front-row lateral order (w ascending = nearer
    the rail) must equal post order; a second row (fields > 9) is checked for presence only (DR-04)."""
    rows = autostart_rows or {}
    n = field_size or len(post_positions)
    front = {s for s in post_positions if rows.get(s, 1 if post_positions[s] <= 9 or n <= 9 else 2) == 1}
    vis_front = [s for s in lineup if s in front]
    if len(vis_front) < 2:
        return StartResult("inconclusive", ["fewer than 2 front-row runners visible"])
    by_lat = sorted(vis_front, key=lambda s: lineup[s][1])
    by_post = sorted(vis_front, key=lambda s: post_positions[s])
    if by_lat != by_post:
        return StartResult("mismatch", [f"front-row lateral order {by_lat} != post order {by_post}"])
    second = [s for s in lineup if s not in front]
    return StartResult("pass", [f"second row present: {sorted(second)}"] if second else [])


def start_check_volte(lineup: dict[int, tuple[float, float]], rendement_m: dict[int, int], band_sep_min_sl: float = 2.0) -> StartResult:
    """Volte bands at their marks: cluster visible runners longitudinally; clusters MUST order by mark
    (larger rendement further back) and each runner MUST sit in its band's cluster. Within-band order is never checked."""
    vis = [s for s in lineup if s in rendement_m]
    if len(vis) < 2:
        return StartResult("inconclusive", ["fewer than 2 runners visible"])
    bands_present = sorted({rendement_m[s] for s in vis})
    if len(bands_present) == 1:
        return StartResult("pass", ["single band visible"])
    order = sorted(vis, key=lambda s: -lineup[s][0])   # front first
    clusters: list[list[int]] = [[order[0]]]
    for a, b in pairwise(order):
        if lineup[a][0] - lineup[b][0] >= band_sep_min_sl:
            clusters.append([b])
        else:
            clusters[-1].append(b)
    if len(clusters) != len(bands_present):
        return StartResult("inconclusive", [f"{len(clusters)} longitudinal clusters for {len(bands_present)} bands (poor separation)"])
    for cluster, band in zip(clusters, bands_present):      # front cluster = smallest rendement
        wrong = [s for s in cluster if rendement_m[s] != band]
        if wrong:
            return StartResult("mismatch", [f"runners {wrong} not in their band cluster (band {band} m)"])
    return StartResult("pass")
