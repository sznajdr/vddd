"""M3 consistency checks — STUB with the normative contract spelled out (SPEC-2.0.0-draft §4 M3 DoD; D-23, D-25, D-30, D-34; L-21…L-24).

Finish check (a): t_end on first past the post. Reference order = provisional/photo if ingested,
else final order restricted to non-revision-implicated runners, excluding NP/DAI/DQ.
finish_check_basis in {provisional, final_unrevised, final_assumed, final_revision_carveout, unavailable}.
Reconstruct observed crossings only; compare only runners present in the reference.
First-past ladder: (i) observed_crossing; (ii) official adopted iff >= finish_evidence_min_k observed
crossings all consistent with the reference AND no revision evidence -> official_unrevised /
official_assumed; zero or insufficient observations -> first_past_saddle_no = NULL, EC-12 inconclusive
(D-30, never official_assumed on no evidence); (iii) contradiction -> human_confirm; (iv) NULL.
Start check (b): autostart -> front row lateral order = post order, second row presence only (DR-04);
volte -> rendement bands at marks, within-band order never inferred.
EC-12: |(tend - t0) - official_elapsed_norm_s(first_past) - anchor_offset_<start_type>_s| > anchor_tol_<start_type>_s
-> one re-click, then mismatch/anchor_suspect. unavailable/unresolved -> inconclusive.
EC-14: recall suspected -> t_0 on the FINAL release; flag surfaced, never auto-corrected.
Checks are non-corrective. Post-hoc observations never assign identity (D-01).
"""


def finish_check(*args, **kwargs):
    raise NotImplementedError("M3 finish check: SPEC-2.0.0-draft §4 M3 DoD (a); needs tracklets + finish shot")


def start_check(*args, **kwargs):
    raise NotImplementedError("M3 start check: SPEC-2.0.0-draft §4 M3 DoD (b)")


def anchor_check(video_duration_s: float, official_elapsed_norm_s: float | None, start_type: str, ts) -> dict:
    """EC-12 under D-34 (per-start-type offset + tolerance). Implemented because it is pure arithmetic;
    values are evidence-gated until OD-1x."""
    if official_elapsed_norm_s is None:
        return {"anchor_check_status": "inconclusive", "anchor_duration_delta_s": None, "anchor_suspect": False}
    offset = float(ts[f"anchor_offset_{start_type}_s"])
    tol = float(ts[f"anchor_tol_{start_type}_s"])
    delta = video_duration_s - official_elapsed_norm_s
    status = "pass" if abs(delta - offset) <= tol else "mismatch"
    return {"anchor_check_status": status, "anchor_duration_delta_s": delta, "anchor_suspect": status == "mismatch"}
