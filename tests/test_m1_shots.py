import shutil
from itertools import pairwise

import numpy as np
import pytest

from tripstate.m1_shots import boundary_f1, duplicate_fraction, segment, type_accuracy
from tripstate.pilot import FrameSource
from tripstate.synth import scripted_race
from tripstate.synth.broadcast import render_broadcast

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

SCRIPT = [(0.0, 6.0, "wide_pan"), (6.0, 8.0, "tight"), (8.0, 12.0, "wide_pan"), (12.0, 14.0, "head_on"),
          (14.0, 17.0, "replay_insert"), (17.0, 18.0, "graphic_fullscreen"), (18.0, 20.0, "wide_pan")]


@pytest.fixture(scope="module")
def broadcast(tmp_path_factory):
    race = scripted_race(duration_s=20.0)
    out = tmp_path_factory.mktemp("m1") / "broadcast.mp4"
    truth = render_broadcast(race, out, size=(320, 180), script=SCRIPT, banner=(9.0, 11.0), replay_source=(2.0, 3.5))
    frames = FrameSource(out).frame_cache()
    return truth, frames


def test_segmenter_meets_m1_acceptance_on_synthetic_broadcast(broadcast, ts):
    truth, frames = broadcast
    shots, _masks = segment(frames, 25.0, ts)
    # contiguous, non-overlapping, full coverage
    assert shots[0].t_start_video_s == 0.0 and abs(shots[-1].t_end_video_s - len(frames) / 25.0) < 1e-9
    assert all(abs(a.t_end_video_s - b.t_start_video_s) < 1e-9 for a, b in pairwise(shots))
    pred_cuts = [s.t_start_video_s for s in shots[1:]]
    true_cuts = [a for a, _, _ in truth["shots"][1:]]
    bf = boundary_f1(pred_cuts, true_cuts, 0.5)
    assert bf["f1"] >= 0.9, (bf, pred_cuts)
    ta = type_accuracy(shots, truth["shots"])
    assert ta["wide_pan_accuracy"] >= 0.95 and ta["type_accuracy"] >= 0.85, (ta, [(s.t_start_video_s, s.type) for s in shots])
    assert any(s.type == "replay_insert" for s in shots)        # EC-07: the slow-motion insert is not a wide pan
    banner_shot = next(s for s in shots if s.t_start_video_s <= 9.5 < s.t_end_video_s)
    assert banner_shot.graphic_overlay_mask_ref and banner_shot.overlay_fraction > 0.02   # EC-06 lower third found
    clean = next(s for s in shots if s.t_start_video_s <= 1.0 < s.t_end_video_s)
    assert clean.overlay_fraction < 0.01


def test_duplicate_fraction_detects_slow_motion():
    a = np.zeros((40, 40, 3), np.uint8); b = np.full((40, 40, 3), 90, np.uint8)
    assert duplicate_fraction([a, a, b, b, a, a]) > 0.5
    assert duplicate_fraction([a, b, a, b]) == 0.0


def test_boundary_f1_matching():
    r = boundary_f1([1.0, 5.2, 9.0], [1.1, 5.0, 12.0], 0.5)
    assert r["tp"] == 2 and abs(r["f1"] - 2 / 3) < 1e-9
