"""D2 — property-based invariant tests (SPEC-2.0.0-draft §2.3, §2.6, §3.4, §9; D-32).

Random M4 geometry streams go through chart_race; the normative shape rules must hold for every input:
exactly one base segment per charted instant, overlays inside visible base time, half-open adjacent intervals,
at most one lead_uncovered_outside per instant, canonical export invariant under row shuffling, and marker
binding invariant under edits that do not touch markers."""
import random
import re
from itertools import pairwise

from hypothesis import given, settings
from hypothesis import strategies as st

from tripstate.config import load_default
from tripstate.m5_states.smoothing import FrameGeom, chart_race
from tripstate.m8_storage.canonical import canonical_jsonl, ordinal_ids
from tripstate.release.freeze import DRAFT_PATH, KILL_GATES_PATH, REGISTRY_PATH, load_yaml
from tripstate.release.markers import MARKER_RE, bind_markers

TS = load_default()
FPS = 25.0
EPS = 1e-9


@st.composite
def geometry_stream(draw):
    n_runners = draw(st.integers(2, 6))
    n_frames = draw(st.integers(6, 24))
    saddles = list(range(1, n_runners + 1))
    # a few "lanes" and longitudinal spots so states actually vary; occasional dropouts / low confidence / unresolved tiers
    frames = {}
    for s in saddles:
        seq = []
        l0, w0 = draw(st.floats(-6.0, 1.0)), draw(st.sampled_from([0.0, 0.3, 1.0, 1.3, 2.0, 2.4]))
        for i in range(n_frames):
            detected = draw(st.booleans()) if draw(st.integers(0, 9)) == 0 else True
            if not detected:
                seq.append(FrameGeom(i / FPS, False, 0.0))
                continue
            conf = draw(st.sampled_from([0.2, 0.5, 0.95, 0.95]))
            l = l0 + draw(st.floats(-0.4, 0.4)) + (0.1 * i if draw(st.booleans()) else 0.0)
            w = w0 + draw(st.floats(-0.2, 0.2))
            tier = (round(w) + 1 if w > -0.5 else None) if draw(st.integers(0, 7)) else None
            seq.append(FrameGeom(i / FPS, True, conf, l, w, tier))
        frames[s] = seq
    # charted intervals: whole race, or two sub-intervals with a gap (EC-01 truncation)
    tend = n_frames / FPS
    if n_frames >= 12 and draw(st.booleans()):
        cut = draw(st.integers(3, n_frames - 6))
        gap = draw(st.integers(1, 3))
        intervals = [(0.0, cut / FPS), ((cut + gap) / FPS, tend)]
    else:
        intervals = [(0.0, tend)]
    return frames, [i / FPS for i in range(n_frames)], intervals, 0.0, tend


def _frac_intervals(intervals, t0, tend):
    return [((a - t0) / (tend - t0), (b - t0) / (tend - t0)) for a, b in intervals]


@settings(max_examples=20, deadline=None)
@given(geometry_stream())
def test_chart_race_shape_invariants(stream):
    frames, times, intervals, t0, tend = stream
    rows = chart_race(frames, times, intervals, t0, tend, TS)
    charted = _frac_intervals(intervals, t0, tend)
    for s in frames:
        base = sorted((r for r in rows if r["saddle_no"] == s and r["state_kind"] == "base"), key=lambda r: r["t_start_frac"])
        # every interval is half-open, non-empty, inside [0, 1]
        for r in base:
            assert 0.0 <= r["t_start_frac"] < r["t_end_frac"] <= 1.0 + EPS
        # base segments partition the charted time: adjacent inside an interval, never overlapping, no gap inside an interval
        for a, b in pairwise(base):
            assert b["t_start_frac"] >= a["t_end_frac"] - EPS
            same_interval = any(x - EPS <= a["t_start_frac"] and b["t_end_frac"] <= y + EPS for x, y in charted)
            if same_interval:
                assert abs(b["t_start_frac"] - a["t_end_frac"]) < 1e-6
        if base:
            covered = sum(r["t_end_frac"] - r["t_start_frac"] for r in base)
            assert abs(covered - sum(y - x for x, y in charted)) < 1e-6
            assert abs(base[0]["t_start_frac"] - charted[0][0]) < 1e-6 and abs(base[-1]["t_end_frac"] - charted[-1][1]) < 1e-6
        # overlays stay inside visible base time of the same runner
        visible = [(r["t_start_frac"], r["t_end_frac"]) for r in base if r["visibility"] == "visible"]
        for o in (r for r in rows if r["saddle_no"] == s and r["state_kind"] == "overlay"):
            assert o["state"] in ("DETACHED", "LOW_CONF") and o["t_start_frac"] < o["t_end_frac"]
            assert any(x - EPS <= o["t_start_frac"] and o["t_end_frac"] <= y + EPS for x, y in visible), (o, visible)
        # payload constraints (§9): covered NULL only on abstentions; lead flags consistent with the state
        for r in base:
            if r["state"] in ("NOT_VISIBLE", "UNKNOWN"):
                assert r["covered"] is None and r["lead_uncovered_outside"] is None
            else:
                assert isinstance(r["covered"], bool)
                if r["state"] != "PARKED":
                    assert r["lead_uncovered_outside"] is False
    # at most one lead_uncovered_outside = true per instant (sample every base boundary)
    instants = sorted({r["t_start_frac"] for r in rows} | {(r["t_start_frac"] + r["t_end_frac"]) / 2 for r in rows})
    for t in instants:
        leads = [r["saddle_no"] for r in rows if r["state_kind"] == "base" and r["lead_uncovered_outside"] is True
                 and r["t_start_frac"] <= t < r["t_end_frac"]]
        assert len(leads) <= 1, (t, leads)


@settings(max_examples=15, deadline=None)
@given(geometry_stream(), st.integers(0, 10_000))
def test_canonical_export_is_invariant_under_row_order(stream, seed):
    frames, times, intervals, t0, tend = stream
    rows = [dict(r, race_id="R") for r in chart_race(frames, times, intervals, t0, tend, TS)]
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    cols = ["race_id", "saddle_no", "seg_id", "state_kind", "state", "covered", "lead_uncovered_outside",
            "lead_uncovered_outside_ambiguous", "tier_attr", "end_attr", "method", "t_start_frac", "t_end_frac",
            "confidence", "visibility", "start_truncated", "end_truncated"]
    a = canonical_jsonl(ordinal_ids(rows, "seg_id", "t_start_frac"), cols, ["race_id", "saddle_no", "seg_id"])
    b = canonical_jsonl(ordinal_ids(shuffled, "seg_id", "t_start_frac"), cols, ["race_id", "saddle_no", "seg_id"])
    assert a == b
    ids = [r["seg_id"] for r in ordinal_ids(rows, "seg_id", "t_start_frac")]
    assert ids == list(range(len(rows)))                        # zero-based ordinals, no gaps (§9)


DRAFT = DRAFT_PATH.read_text(encoding="utf-8")
REGISTRY, GATES = load_yaml(REGISTRY_PATH), load_yaml(KILL_GATES_PATH)
BASELINE = [(b.kind, b.keys, b.nums, b.replacement) for b in bind_markers(DRAFT, REGISTRY, GATES)]


@settings(max_examples=8, deadline=None)
@given(st.lists(st.tuples(st.integers(0, 10_000), st.text(alphabet="abcdefghij ", min_size=1, max_size=20)), min_size=1, max_size=8),
       st.integers(0, 10_000))
def test_marker_binding_is_stable_under_edits_that_do_not_touch_markers(edits, blank_at):
    lines = DRAFT.splitlines()
    marker_lines = {i for i, ln in enumerate(lines) if MARKER_RE.search(ln) or "`[OPEN" in ln}
    out = list(lines)
    for pos, words in edits:
        i = pos % len(out)
        if i in marker_lines or out[i].startswith("|") or out[i].startswith("#"):
            continue                              # tables/headings keep their shape; marker lines are the subject under test
        out[i] = out[i] + " " + words
    out.insert(blank_at % len(out), "")
    edited = "\n".join(out) + "\n"
    got = [(b.kind, b.keys, b.nums, b.replacement) for b in bind_markers(edited, REGISTRY, GATES)]
    assert got == BASELINE
    assert len(re.findall(r"`\[EG", edited)) == len(re.findall(r"`\[EG", DRAFT))
