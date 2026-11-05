"""C3 — environment fingerprint for versions.determinism_env (D-32): actual values, null for absent, stable."""
import json
import subprocess
import sys
from pathlib import Path

from tripstate.m8_storage import Store
from tripstate.m8_storage.determinism import (
    fingerprint,
    fingerprint_json,
    versions_row,
    weight_hashes,
)

ROOT = Path(__file__).resolve().parents[1]


def test_fingerprint_is_stable_and_records_only_what_exists(tmp_path):
    a, b = fingerprint(seed=7), fingerprint(seed=7)
    assert a == b and fingerprint_json(seed=7) == fingerprint_json(seed=7)
    assert a["python"] and a["numpy"] and a["seed"] == 7 and a["batch_size"] is None and a["half_precision"] is None
    assert set(a["torch"]) >= {"torch", "cuda", "cudnn", "use_deterministic_algorithms", "tf32_matmul"}
    try:
        import torch  # noqa: F401
        assert a["torch"]["torch"] is not None
    except ImportError:
        assert all(v is None for v in a["torch"].values())
    assert list(a) == sorted(a)
    w = tmp_path / "w.pt"
    w.write_bytes(b"weights")
    h = weight_hashes([w, tmp_path / "missing.pt"])
    assert len(h["w.pt"]) == 64 and h["missing.pt"] is None
    assert fingerprint(weights=[w]) != a


def test_versions_row_round_trips_through_the_store(tmp_path):
    st = Store()
    row = versions_row("cv-0.1", "cv_extract", "extractor-x", {"tripstate": "abc"}, seed=1, batch_size=4)
    st.insert("versions", [row], producer_version="cv-0.1", created_at="2026-11-04T00:00:00")
    back = st.rows("versions")[0]
    env = json.loads(back["determinism_env"])
    assert env["seed"] == 1 and env["batch_size"] == 4 and json.loads(back["module_git_hashes"]) == {"tripstate": "abc"}
    cli = subprocess.run([sys.executable, str(ROOT / "tools/env_fingerprint.py"), "--seed", "3", "--out", str(tmp_path / "fp.json")],
                         capture_output=True, text=True, check=False)
    assert cli.returncode == 0 and json.loads((tmp_path / "fp.json").read_text())["seed"] == 3
    db = tmp_path / "s.sqlite"
    ins = subprocess.run([sys.executable, str(ROOT / "tools/env_fingerprint.py"), "--store", str(db), "--producer-version", "pv1",
                          "--created-at", "2026-11-04T00:00:00"], capture_output=True, text=True, check=False)
    assert ins.returncode == 0 and "inserted" in ins.stdout
    again = subprocess.run([sys.executable, str(ROOT / "tools/env_fingerprint.py"), "--store", str(db), "--producer-version", "pv1"],
                           capture_output=True, text=True, check=False)
    assert again.returncode == 1 and "already exists" in again.stdout
