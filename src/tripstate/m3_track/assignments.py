"""`id_assignments` rows from operator seeds (SPEC-2.0.0-draft §4 M3, §9; D-01; RP-18 / L-51).

A seed is the operator's click: (frame, saddle number, x, y in source-frame pixels). It binds one tracklet (a
tracker id, or the SAM 2 object id of the prompt) to a saddle number from that frame on; later clicks on the same
runner are `human_correction`. RP-18 keeps the click itself as provenance — `seed_x_px`, `seed_y_px` and
`seed_box_ref` (`"<kind>:<tracklet_id>@<frame>"`, the box or mask the click landed in) — so every seeding action
doubles as future re-ID training data at zero operator cost. These pixels are identity provenance; they are never
state coordinates (§3.3's pixel ban is about geometry, not about recording where a human clicked)."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, is_dataclass
from typing import Any

METHODS = {"human_seed": "human_seed", "human_correction": "human_correction"}


def _seed_dict(seed: Any) -> dict:
    return asdict(seed) if is_dataclass(seed) else dict(seed)


def box_ref(kind: str, tracklet_id: int, frame: int) -> str:
    return f"{kind}:{tracklet_id}@{frame}"


def id_assignment_rows(race_id: str, shot_id: int, seeds: Iterable[Any], tracklet_for: Callable[[dict], int | None],
                       fps: float | None = None, ref_kind: str = "track", human_confirmed: bool = True) -> list[dict]:
    """One row per seed that hit a tracklet. `seeds` are `tripstate.seeding.session.Seed`s or dicts with
    frame, saddle_no, x, y, kind (and t_s when fps is not given). `tracklet_for(seed)` returns the tracklet id
    the click landed on (None = missed, no row: a flag, not an assignment). Rows carry no version columns."""
    rows: list[dict] = []
    for raw in seeds:
        s = _seed_dict(raw)
        tid = tracklet_for(s)
        if tid is None:
            continue
        frame = int(s["frame"])
        t_s = s.get("t_s") if s.get("t_s") is not None else (frame / fps if fps else None)
        rows.append({
            "race_id": race_id, "shot_id": int(shot_id), "tracklet_id": int(tid), "saddle_no": int(s["saddle_no"]),
            "method": METHODS.get(s.get("kind", "human_seed"), "human_seed"), "human_confirmed": bool(human_confirmed),
            "seed_frame": frame, "seed_video_s": t_s,
            "seed_x_px": float(s["x"]), "seed_y_px": float(s["y"]), "seed_box_ref": box_ref(ref_kind, int(tid), frame),
        })
    rows.sort(key=lambda r: (r["seed_frame"], r["saddle_no"], r["tracklet_id"]))
    return rows


def rows_from_pilot(race_id: str, shot_id: int, seeds: Iterable[Any], assignment: Mapping[int, int], tracks: Mapping[int, Any],
                    fps: float | None = None) -> list[dict]:
    """Pilot comparison path: `assignment` = {track_id: saddle_no} from assign_seeds_to_tracks; a seed maps to the
    track that carries its saddle number and has a box on the seed frame."""
    def tracklet_for(s: dict) -> int | None:
        for tid, sad in assignment.items():
            if sad == s["saddle_no"] and s["frame"] in getattr(tracks[tid], "boxes", {}):
                return tid
        return None
    return id_assignment_rows(race_id, shot_id, seeds, tracklet_for, fps, ref_kind="track")


def rows_from_session(race_id: str, shot_id: int, session_result: Mapping[str, Any]) -> list[dict]:
    """Seeded (SAM 2 / live engine) path: the prompt's object id is the saddle number, so tracklet_id = saddle_no and
    the reference points at the mask the prompt created."""
    fps = session_result.get("fps")
    return id_assignment_rows(race_id, shot_id, session_result.get("seeds", []), lambda s: int(s["saddle_no"]), fps, ref_kind="mask")
