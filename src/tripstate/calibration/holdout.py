"""§7.2 step 4: report ONCE on the held-out races. No iteration against held-out. If the held-out headline collapses
versus dev by more than `heldout_gap_max_pt` points (TS `calibration` namespace), the state definitions — not the
thresholds — are suspect: the verdict is `spec_revision`, never "tune more". Produces the changelog row draft §14
requires for every held-out evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field

from tripstate.calibration.search import DevRace, score_candidate
from tripstate.config import ThresholdSet
from tripstate.evaluation.scoring import SetScore, score_set


@dataclass
class HeldoutResult:
    dev_headline: float | None
    heldout: SetScore
    gap_pt: float | None
    gap_max_pt: float
    verdict: str                      # accept | spec_revision | not_evaluable
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"dev_headline": self.dev_headline, "heldout": self.heldout.as_dict(), "gap_pt": self.gap_pt,
                "gap_max_pt": self.gap_max_pt, "verdict": self.verdict, "notes": self.notes}


def evaluate_heldout(ts: ThresholdSet, heldout_races: list[DevRace], dev_headline: float | None) -> HeldoutResult:
    if not heldout_races:
        return HeldoutResult(dev_headline, score_set([]), None, float(ts["heldout_gap_max_pt"]), "not_evaluable", ["no held-out races"])
    if any(r.split != "heldout" for r in heldout_races):
        raise ValueError("held-out evaluation takes held-out races only")
    scores, _ = score_candidate(ts, heldout_races)
    ho = score_set(scores)
    gap_max = float(ts["heldout_gap_max_pt"])
    if dev_headline is None or ho.headline is None:
        return HeldoutResult(dev_headline, ho, None, gap_max, "not_evaluable", ["a headline is undefined (empty DoD-1 union)"])
    gap = 100.0 * (dev_headline - ho.headline)
    verdict = "spec_revision" if gap > gap_max else "accept"
    notes = [] if verdict == "accept" else [f"dev − held-out gap {gap:.1f} pt > {gap_max:g} pt: open a spec revision; do not tune further (§7.2 step 4)"]
    return HeldoutResult(dev_headline, ho, gap, gap_max, verdict, notes)


def changelog_row(spec_version: str, date: str, ts_version: str, extractor_version: str, res: HeldoutResult) -> str:
    ho = res.heldout

    def f(x: float | None) -> str:
        return "—" if x is None else f"{x:.3f}"
    return (f"| {spec_version} | {date} | Held-out evaluation (§6.3) with `extractor_version = {extractor_version}`, "
            f"`threshold_set_version = {ts_version}`: headline dev {f(res.dev_headline)} / held-out {f(ho.headline)} "
            f"(gap {'—' if res.gap_pt is None else f'{res.gap_pt:.1f}'} pt, limit {res.gap_max_pt:g}); uncovered-outside IoU {f(ho.uncovered_outside_iou)}, "
            f"covered IoU {f(ho.covered_iou)}, rest macro {f(ho.rest_macro)} over {ho.n_races} held-out races. Verdict: {res.verdict}. |")
