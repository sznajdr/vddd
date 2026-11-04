"""Operator-loop state machine for the seeding tool.

Keymap (M3 tool DoD; one key per action):
  space        play / pause                     , .      step -1 / +1 frame
  [ ]          jump to previous / next unresolved flag
  1 2 4 8      playback speed (auto-slowdown to 1x near an unresolved flag, pause on it — DR-12)
  click        select runner at (x, y) on the current frame, then type the saddle number + Enter
  o            confirm proposed orientation (travel direction + rail side) for the current shot
  O / R        flip travel direction / rail side (human correction)
  t / e        capture t_0 / t_end anchor on the current frame (D-10; EC-04 semantics shown)
  r            raise / clear the "possible recall" flag (EC-14)
  a / x        accept / reject the break candidate at the playhead (M6 loop)
  f            confirm first-past runner: type saddle number + Enter (M3 DoD (a))
  Escape       cancel a pending number entry
  q            finish: write seeds, anchors, decisions and human-minutes (DoD-3, Q-7)
Human-minutes = wall-clock from the first keypress/click to `q`, including adjudication prompts.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

KEYMAP = {
    " ": "play_pause", ",": "step_back", ".": "step_fwd", "[": "prev_flag", "]": "next_flag",
    "1": "speed_1", "2": "speed_2", "4": "speed_4", "8": "speed_8",
    "o": "confirm_orientation", "O": "flip_travel", "R": "flip_rail",
    "t": "anchor_t0", "e": "anchor_tend", "r": "toggle_recall",
    "a": "accept_candidate", "x": "reject_candidate", "f": "first_past",
    "Escape": "cancel", "Enter": "enter", "q": "finish",
}
SPEEDS = {"speed_1": 1, "speed_2": 2, "speed_4": 4, "speed_8": 8}


@dataclass
class Seed:
    frame: int
    t_s: float
    saddle_no: int
    x: float
    y: float
    kind: str = "human_seed"          # human_seed | human_correction


@dataclass
class Flag:
    frame: int
    kind: str                         # cut | low_conf | overlap | lost | custom
    saddle_no: int | None = None
    note: str = ""
    resolved: bool = False


@dataclass
class Candidate:
    frame_start: int
    frame_end: int | None
    saddle_no: int
    status: str = "pending"           # pending | accepted | rejected


@dataclass
class Orientation:
    travel_direction_sign: int
    rail_side: str
    confidence: float
    confirmed: bool = False
    method: str = "heuristic"         # heuristic | human_confirm


class SeedingSession:
    def __init__(
        self,
        race_id: str,
        n_frames: int,
        fps: float,
        *,
        start_type: str,
        start_format: str,
        rendement_bands: dict[int, int] | None = None,
        budget_cap_min: float = 8.0,
        clock: Callable[[], float] = time.monotonic,
        flags: list[Flag] | None = None,
        candidates: list[Candidate] | None = None,
        orientation: Orientation | None = None,
        slowdown_window_frames: int = 25,
    ):
        self.race_id, self.n_frames, self.fps = race_id, n_frames, fps
        self.start_type, self.start_format = start_type, start_format
        self.rendement_bands = rendement_bands or {}
        self.budget_cap_min = budget_cap_min
        self.clock = clock
        self.flags = list(flags or [])
        self.candidates = sorted(candidates or [], key=lambda c: (c.frame_start, c.saddle_no))
        self.orientation = orientation
        self.slowdown_window = slowdown_window_frames
        self.index = 0
        self.playing = False
        self.speed = 1
        self.seeds: list[Seed] = []
        self.t0_frame: int | None = None
        self.tend_frame: int | None = None
        self.first_past_saddle_no: int | None = None
        self.recall_suspected = False
        self.pending_click: tuple[float, float] | None = None
        self.awaiting: str | None = None    # 'seed' | 'first_past'
        self.number_buffer = ""
        self.log: list[dict] = []
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.messages: list[str] = []
        self.headless = False   # set by scripted replays: wall-clock figures are then meaningless

    # ---- helpers ---------------------------------------------------------------------------
    @property
    def t_s(self) -> float:
        return self.index / self.fps

    def _log(self, action: str, **details) -> None:
        now = self.clock()
        if self.started_at is None:
            self.started_at = now
        self.log.append({"wall_s": now, "frame": self.index, "action": action, **details})

    def _say(self, msg: str) -> None:
        self.messages.append(msg)

    def human_minutes(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.finished_at if self.finished_at is not None else self.clock()
        return (end - self.started_at) / 60.0

    def over_budget(self) -> bool:
        m = self.human_minutes()
        return m is not None and m > self.budget_cap_min

    def unresolved_flags(self) -> list[Flag]:
        return [f for f in self.flags if not f.resolved]

    def current_candidate(self) -> Candidate | None:
        for c in self.candidates:
            if c.status == "pending" and c.frame_start <= self.index <= (c.frame_end if c.frame_end is not None else c.frame_start + int(self.fps * 2)):
                return c
        return None

    def start_prompt(self) -> str:
        """What the tool shows before anchor capture (EC-04): start type/format + bands."""
        if self.start_type == "autostart":
            return "autostart: t_0 = gate-car pull-away"
        bands = ", ".join(f"{b} m: {n} runners" for b, n in sorted(self.rendement_bands.items())) or "flat"
        return f"volte ({self.start_format}): t_0 = FINAL release into racing direction; bands {bands}"

    # ---- playback -------------------------------------------------------------------------
    def tick(self) -> None:
        """Advance one UI tick while playing: `speed` frames, capped to 1x near an unresolved flag
        and paused on it (DR-12 auto-slowdown)."""
        if not self.playing:
            return
        ahead = [f for f in self.unresolved_flags() if self.index < f.frame <= self.index + self.slowdown_window]
        step = 1 if ahead else self.speed
        nxt = min(self.n_frames - 1, self.index + step)
        for f in sorted(ahead, key=lambda f: f.frame):
            if self.index < f.frame <= nxt:
                nxt = f.frame
                self.playing = False
                self._say(f"flag {f.kind} at frame {f.frame}" + (f" (runner {f.saddle_no})" if f.saddle_no else ""))
                break
        self.index = nxt
        if self.index >= self.n_frames - 1:
            self.playing = False

    def _jump_flag(self, direction: int) -> None:
        fl = sorted(self.unresolved_flags(), key=lambda f: f.frame)
        cands = [f for f in fl if (f.frame > self.index if direction > 0 else f.frame < self.index)]
        if cands:
            target = cands[0] if direction > 0 else cands[-1]
            self.index = target.frame
            self.playing = False

    # ---- input ----------------------------------------------------------------------------
    def click(self, x: float, y: float) -> None:
        self.pending_click = (x, y)
        self.awaiting = "seed"
        self.number_buffer = ""
        self.playing = False
        self._log("click", x=x, y=y)

    def key(self, k: str) -> None:
        if self.finished_at is not None:
            return
        if self.awaiting and k.isdigit():
            self.number_buffer += k
            return
        action = KEYMAP.get(k)
        if action is None:
            return
        if self.started_at is None:
            self._log("first_input", key=k)
        getattr(self, f"_do_{action}")()

    # ---- actions --------------------------------------------------------------------------
    def _do_play_pause(self) -> None:
        self.playing = not self.playing
        self._log("play" if self.playing else "pause")

    def _do_step_back(self) -> None:
        self.index = max(0, self.index - 1); self.playing = False

    def _do_step_fwd(self) -> None:
        self.index = min(self.n_frames - 1, self.index + 1); self.playing = False

    def _do_prev_flag(self) -> None:
        self._jump_flag(-1)

    def _do_next_flag(self) -> None:
        self._jump_flag(+1)

    def _set_speed(self, s: int) -> None:
        self.speed = s; self._log("speed", speed=s)

    def _do_speed_1(self) -> None: self._set_speed(1)
    def _do_speed_2(self) -> None: self._set_speed(2)
    def _do_speed_4(self) -> None: self._set_speed(4)
    def _do_speed_8(self) -> None: self._set_speed(8)

    def _do_confirm_orientation(self) -> None:
        if self.orientation is None:
            self._say("no orientation proposal for this shot"); return
        self.orientation.confirmed = True
        self.orientation.method = "human_confirm"
        self._log("orientation_confirm", travel=self.orientation.travel_direction_sign, rail=self.orientation.rail_side)

    def _do_flip_travel(self) -> None:
        if self.orientation is None:
            return
        self.orientation.travel_direction_sign *= -1
        self.orientation.confirmed, self.orientation.method = True, "human_confirm"
        self._log("orientation_flip_travel", travel=self.orientation.travel_direction_sign)

    def _do_flip_rail(self) -> None:
        if self.orientation is None:
            return
        self.orientation.rail_side = "left_of_travel" if self.orientation.rail_side == "right_of_travel" else "right_of_travel"
        self.orientation.confirmed, self.orientation.method = True, "human_confirm"
        self._log("orientation_flip_rail", rail=self.orientation.rail_side)

    def _do_anchor_t0(self) -> None:
        self.t0_frame = self.index; self._log("anchor_t0", prompt=self.start_prompt())

    def _do_anchor_tend(self) -> None:
        self.tend_frame = self.index; self._log("anchor_tend")

    def _do_toggle_recall(self) -> None:
        self.recall_suspected = not self.recall_suspected
        self._log("recall_flag", suspected=self.recall_suspected)
        if self.recall_suspected:
            self._say("possible recall: re-anchor t_0 on the FINAL release (EC-14)")

    def _review(self, status: str) -> None:
        c = self.current_candidate()
        if c is None:
            self._say("no pending break candidate at the playhead"); return
        c.status = status
        self._log("candidate_" + status, saddle_no=c.saddle_no, frame_start=c.frame_start)

    def _do_accept_candidate(self) -> None: self._review("accepted")
    def _do_reject_candidate(self) -> None: self._review("rejected")

    def _do_first_past(self) -> None:
        self.awaiting = "first_past"; self.number_buffer = ""; self.playing = False

    def _do_cancel(self) -> None:
        self.awaiting, self.pending_click, self.number_buffer = None, None, ""

    def _do_enter(self) -> None:
        if not self.awaiting or not self.number_buffer:
            return
        n = int(self.number_buffer)
        if self.awaiting == "seed" and self.pending_click is not None:
            x, y = self.pending_click
            kind = "human_correction" if any(s.saddle_no == n for s in self.seeds) else "human_seed"
            self.seeds.append(Seed(self.index, self.t_s, n, x, y, kind))
            for f in self.flags:
                if not f.resolved and f.frame <= self.index and (f.saddle_no in (None, n)):
                    f.resolved = True
            self._log("seed", saddle_no=n, kind=kind, x=x, y=y)
        elif self.awaiting == "first_past":
            self.first_past_saddle_no = n
            self._log("first_past_confirm", saddle_no=n)
        self.awaiting, self.pending_click, self.number_buffer = None, None, ""

    def _do_finish(self) -> None:
        self.finished_at = self.clock()
        self._log("finish")

    # ---- output ---------------------------------------------------------------------------
    def seeding_seconds_initial(self) -> float | None:
        """OD-1x step 1 / KG-1: wall-clock from the first click to the last initial (non-correction) seed."""
        clicks = [e["wall_s"] for e in self.log if e["action"] == "click"]
        seeds = [e["wall_s"] for e in self.log if e["action"] == "seed" and e.get("kind") == "human_seed"]
        if not clicks or not seeds:
            return None
        return seeds[-1] - clicks[0]

    def result(self) -> dict:
        hm = self.human_minutes()
        return {
            "race_id": self.race_id, "fps": self.fps, "n_frames": self.n_frames,
            "seeds": [asdict(s) for s in self.seeds],
            "anchors": {"t0_frame": self.t0_frame, "t0_video_s": None if self.t0_frame is None else self.t0_frame / self.fps,
                        "tend_frame": self.tend_frame, "tend_video_s": None if self.tend_frame is None else self.tend_frame / self.fps,
                        "t0_method": "human_click", "tend_method": "human_click"},
            "orientation": None if self.orientation is None else asdict(self.orientation),
            "first_past_saddle_no": self.first_past_saddle_no, "recall_suspected": self.recall_suspected,
            "flags": [asdict(f) for f in self.flags], "candidates": [asdict(c) for c in self.candidates],
            "human_minutes": hm, "over_budget": self.over_budget(), "budget_cap_min": self.budget_cap_min,
            "seeding_seconds_initial": self.seeding_seconds_initial(),
            "finished": self.finished_at is not None, "headless": self.headless, "log": self.log,
        }

    def write(self, out_dir: Path) -> Path:
        out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / "session.json"
        p.write_text(json.dumps(self.result(), indent=1), encoding="utf-8")
        return p
