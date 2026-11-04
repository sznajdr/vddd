"""Live flags inside the seeding loop: engine stepping, monitor, pause-on-flag, re-seed as prompt, timeline export."""
import json

import pytest

from tripstate.pilot.detect import Detection, OracleDetector
from tripstate.pilot.frames import render_synth_video, truth_boxes_from_json
from tripstate.seeding import (
    DetectorLiveEngine,
    FlagMonitor,
    OracleLiveEngine,
    SeedingSession,
    SessionTimelinePropagator,
)
from tripstate.seeding.session import Orientation
from tripstate.synth import scripted_race


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    race = scripted_race(duration_s=8.0)
    out = tmp_path_factory.mktemp("live") / "synth.mp4"
    truth = render_synth_video(race, out, size=(640, 360))
    return race, truth_boxes_from_json(truth), truth["saddles"]


def new_session(n_frames, clock, engine, monitor):
    s = SeedingSession("r1", n_frames, 25.0, start_type="autostart", start_format="autostart", clock=clock,
                       orientation=Orientation(1, "right_of_travel", 0.9))
    s.attach(engine, monitor)
    return s


def play_until(s, pred, max_stops=40):
    """Press play; at each pause, stop if pred(s) holds, else resolve the open flags and continue."""
    for _ in range(max_stops):
        if not s.playing:
            s.key(" ")
        while s.playing:
            s.tick()
        if pred(s) or s.index >= s.n_frames - 1:
            return
        for f in s.unresolved_flags():
            if f.kind != "lost":          # lost flags are left to the engine's own recovery (EC-08 re-match)
                f.resolved = True


def seed_all(s, tb, saddles, frame):
    s.set_index(frame)
    for sad in saddles:
        b = tb[frame][sad]
        s.click((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2)
        for ch in str(sad):
            s.key(ch)
        s.key("Enter")


def test_lost_flag_pauses_and_reseed_resolves(synth, ts):
    race, tb, saddles = synth
    n = len(race.frames())
    engine = OracleLiveEngine(tb, loss_windows={4: [(60, 200)]})       # runner 4's propagation dies at frame 60
    s = new_session(n, Clock(), engine, FlagMonitor(ts, 25.0))
    seed_all(s, tb, saddles, 0)
    assert all(e.get("bound") for e in s.log if e["action"] == "seed")
    s.key("8")
    play_until(s, lambda s: any(f.kind == "lost" and f.saddle_no == 4 and not f.resolved for f in s.flags))
    lost = [f for f in s.flags if f.kind == "lost" and f.saddle_no == 4]
    assert lost and 60 <= lost[0].frame <= 72 and s.index == lost[0].frame and not s.playing   # parked ON the live flag
    assert any("flag lost" in m for m in s.messages[-3:])
    # the scripted occlusion of runner 5 (frames 40-46) was flagged earlier and resolved itself when it came back
    r5 = [f for f in s.flags if f.kind == "lost" and f.saddle_no == 5]
    assert r5 and r5[0].resolved and any("runner 5 back" in m for m in s.messages)
    # operator re-seeds runner 4 where it really is -> new prompt, flag resolved, boxes resume
    b = tb[s.index][4]
    s.click((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2); s.key("4"); s.key("Enter")
    assert lost[0].resolved and s.seeds[-1].kind == "human_correction"
    assert 4 not in engine.boxes_at(s.index)                              # still inside the oracle loss window...
    play_until(s, lambda s: s.index >= s.n_frames - 1)
    assert s.index == n - 1
    assert sum(1 for f in s.flags if f.kind == "lost" and f.saddle_no == 4) >= 1   # ...so it is flagged again after the re-seed


def test_low_conf_and_overlap_flags(synth, ts):
    race, tb, saddles = synth
    n = len(race.frames())
    engine = OracleLiveEngine(tb, conf_dips={2: [(30, 45, 0.2)]})
    mon = FlagMonitor(ts, 25.0)
    s = new_session(n, Clock(), engine, mon)
    seed_all(s, tb, saddles, 0)
    s.key("8")
    play_until(s, lambda s: s.index >= s.n_frames - 1)
    kinds = {(f.kind, f.saddle_no) for f in s.flags}
    assert ("low_conf", 2) in kinds
    assert sum(1 for f in s.flags if f.kind == "low_conf" and f.saddle_no == 2) == 1   # de-duplicated
    # overlap: bind two prompts to the same truth runner (a wrong second click) -> identical boxes
    engine2 = OracleLiveEngine(tb)
    s2 = new_session(n, Clock(), engine2, FlagMonitor(ts, 25.0))
    b = tb[0][1]
    for sad in (1, 9):
        s2.click((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2); [s2.key(c) for c in str(sad)]; s2.key("Enter")
    s2.key("8")
    play_until(s2, lambda s: s.index >= s.n_frames - 1)
    ov = [f for f in s2.flags if f.kind == "overlap"]
    assert ov and ov[0].frame == round(ts["overlap_flag_s"] * 25) - 1


def test_detector_engine_reseed_needed_and_binding(synth, ts):
    race, tb, saddles = synth
    n = len(race.frames())
    det = OracleDetector(tb, seed=3, loss_windows={6: [(40, 95)]})       # runner 6 undetected for 2.2 s > track buffer
    engine = DetectorLiveEngine(det, ts, 25.0)
    s = new_session(n, Clock(), engine, FlagMonitor(ts, 25.0))
    seed_all(s, tb, saddles, 2)
    s.key("8"); s.key(" ")
    stops = []
    while True:
        while s.playing:
            s.tick()
        stops.append((s.index, [(f.kind, f.saddle_no) for f in s.unresolved_flags()]))
        if s.index >= n - 1 or len(stops) > 6:
            break
        if any(f.kind == "reseed_needed" for f in s.unresolved_flags()):
            b = tb[s.index][6]
            s.click((b.x1 + b.x2) / 2, (b.y1 + b.y2) / 2); s.key("6"); s.key("Enter")   # bind the anonymous tracklet
        for f in s.unresolved_flags():
            f.resolved = True
        s.key(" ")
    kinds = [k for _, ks in stops for k in ks]
    assert ("lost", 6) in kinds and ("reseed_needed", None) in kinds
    assert 6 in engine.boxes_at(n - 1)                                     # identity carried on the new tracklet
    tl = engine.timeline()
    assert 6 not in tl.get(60, {}) and 6 in tl.get(150, {})
    assert engine.anonymous_at(n - 1) == {}


def test_timeline_export_round_trip(synth, ts, tmp_path):
    race, tb, saddles = synth
    n = len(race.frames())
    s = new_session(n, Clock(), OracleLiveEngine(tb), FlagMonitor(ts, 25.0))
    seed_all(s, tb, saddles, 0)
    s.key("8")
    play_until(s, lambda s: s.index >= s.n_frames - 1)   # a plain goto would park on the first live flag
    s.key("q")
    p = s.write(tmp_path)
    sess = json.loads(p.read_text())
    assert sess["timeline"] and len(sess["timeline"]) == n
    prop = SessionTimelinePropagator(sess)
    tl = prop.run()
    assert tl[10][1][0].x1 == tb[10][1].x1 and tl[10][1][1] == 1.0
    assert isinstance(tl[10][1][0], Detection)
