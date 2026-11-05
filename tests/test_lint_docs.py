"""Documentation hygiene is enforced, not hoped for (tools/lint_docs.py)."""
import subprocess
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
lint_docs = import_module("lint_docs")


def test_repository_docs_are_clean():
    r = subprocess.run([sys.executable, str(ROOT / "tools/lint_docs.py")], capture_output=True, text=True, cwd=ROOT, check=False)
    assert r.returncode == 0, r.stdout


def test_checks_catch_missing_paths_and_unlisted_tools(tmp_path, monkeypatch):
    assert lint_docs.check_paths() == [] and lint_docs.check_tools_index() == [] and lint_docs.check_package_readmes() == []
    assert "lint-docs" in lint_docs.makefile_targets() and lint_docs.check_make_targets() == []
    monkeypatch.setattr(lint_docs, "CURRENT_STATE", ["README.md"])
    monkeypatch.setattr(lint_docs, "ROOT", tmp_path)
    (tmp_path / "README.md").write_text("see `tools/does_not_exist.py` and `docs/<placeholder>.md`", encoding="utf-8")
    probs = lint_docs.check_paths()
    assert len(probs) == 1 and "tools/does_not_exist.py" in probs[0]
