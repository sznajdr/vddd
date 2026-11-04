from tripstate.seeding import Candidate, Flag, SeedingSession
from tripstate.seeding.session import Orientation


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def session(clock, **kw):
    return SeedingSession("r1", n_frames=1000, fps=25.0, start_type="volte", start_format="volte_handicap",
                          rendement_bands={2850: 8, 2875: 4, 2900: 2}, clock=clock,
                          orientation=Orientation(+1, "right_of_travel", 0.4), **kw)


def type_number(s, n):
    for ch in str(n):
        s.key(ch)
    s.key("Enter")


def test_seed_anchor_orientation_and_human_minutes():
    c = Clock(); s = session(c)
    s.key("o")                                   # first input starts the clock
    assert s.orientation.confirmed and s.orientation.method == "human_confirm"
    s.key("t"); assert s.t0_frame == 0 and "FINAL release" in s.log[-1]["prompt"]
    s.click(100, 200); c.advance(3); type_number(s, 7)
    s.click(300, 200); c.advance(4); type_number(s, 12)
    assert [x.saddle_no for x in s.seeds] == [7, 12] and all(x.kind == "human_seed" for x in s.seeds)
    assert abs(s.seeding_seconds_initial() - 7.0) < 1e-9
    s.index = 999; s.key("e"); assert s.tend_frame == 999
    s.click(110, 210); type_number(s, 7)         # re-seed of a known runner = correction
    assert s.seeds[-1].kind == "human_correction"
    c.advance(60); s.key("q")
    r = s.result()
    assert r["finished"] and abs(r["human_minutes"] - (67 / 60)) < 1e-9 and not r["over_budget"]
    assert r["anchors"]["tend_video_s"] == 999 / 25.0 and r["first_past_saddle_no"] is None


def test_over_budget_flagged_not_waived():
    c = Clock(); s = session(c, budget_cap_min=8.0)
    s.key(" "); c.advance(9 * 60); s.key("q")
    assert s.result()["over_budget"] is True


def test_playback_speed_and_auto_slowdown_at_flag():
    c = Clock(); s = session(c, flags=[Flag(frame=100, kind="low_conf", saddle_no=3)])
    s.key("8"); s.key(" ")
    for _ in range(9):
        s.tick()
    assert s.index == 72                          # 9 ticks at 8x, flag still > 25 frames ahead
    while s.playing:
        s.tick()
    assert s.index == 100 and not s.playing       # slowed to 1x inside the window, paused ON the flag
    assert any("flag low_conf" in m for m in s.messages)
    s.click(50, 50); type_number(s, 3)            # re-seed resolves the flag
    assert s.flags[0].resolved
    s.key(" ")
    for _ in range(3):
        s.tick()
    assert s.index == 124                         # back to 8x once resolved


def test_flag_navigation_and_break_review():
    c = Clock()
    s = session(c, flags=[Flag(200, "cut"), Flag(400, "overlap", 5)],
                candidates=[Candidate(300, 320, 9), Candidate(350, None, 2)])
    s.key("]"); assert s.index == 200
    s.key("]"); assert s.index == 400
    s.key("["); assert s.index == 200
    s.index = 310; s.key("a"); assert s.candidates[0].status == "accepted"
    s.index = 355; s.key("x"); assert s.candidates[1].status == "rejected"
    s.index = 10; s.key("a"); assert "no pending" in s.messages[-1]


def test_first_past_recall_and_flips():
    c = Clock(); s = session(c)
    s.key("f"); type_number(s, 4); assert s.first_past_saddle_no == 4
    s.key("r"); assert s.recall_suspected and "FINAL release" in s.messages[-1]
    s.key("O"); assert s.orientation.travel_direction_sign == -1
    s.key("R"); assert s.orientation.rail_side == "left_of_travel"
    s.key("f"); s.key("5"); s.key("Escape"); assert s.awaiting is None and s.first_past_saddle_no == 4


def test_write_and_no_input_after_finish(tmp_path):
    c = Clock(); s = session(c)
    s.key("t"); s.key("q"); s.key("e")
    assert s.tend_frame is None
    p = s.write(tmp_path)
    assert p.exists() and '"finished": true' in p.read_text()
