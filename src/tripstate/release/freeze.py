"""The D-36 freeze check as a library. Exit-0 semantics: the 2.0.0 promotion is allowed iff `problems` is empty.

Blocks on: an evidence_gated.yaml entry not instantiated (or instantiated without value/evidence); a kill-gate
KG-1…KG-4 not `pass` (KG-5 is advisory: a project gate, not a spec gate); an `[EG]` marker in the draft that binds
to no registry entry / kill-gate or disagrees with the registry's provisional value; an `[OPEN: …]` owner decision
still in the draft; SPEC_STATUS already FROZEN while any of the above remains.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tripstate.release.markers import bind_markers, find_open_markers

ADVISORY_GATES = frozenset({"KG-5"})
ROOT = Path(__file__).resolve().parents[3]
DRAFT_PATH = ROOT / "spec" / "SPEC-2.0.0-draft.md"
REGISTRY_PATH = ROOT / "spec" / "registers" / "evidence_gated.yaml"
KILL_GATES_PATH = ROOT / "spec" / "registers" / "kill_gates.yaml"


@dataclass
class FreezeReport:
    problems: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)
    n_markers: int = 0
    n_bound: int = 0

    @property
    def allowed(self) -> bool:
        return not self.problems


def load_yaml(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def check_freeze(registry: dict, kill_gates: dict, draft_text: str | None, spec_status: str) -> FreezeReport:
    r = FreezeReport()
    for e in registry["entries"]:
        if not e.get("instantiated"):
            r.problems.append(f"EG not instantiated: {e['key']} (provisional {e.get('provisional')})")
        elif e.get("value") is None or not e.get("evidence"):
            r.problems.append(f"EG instantiated without value/evidence: {e['key']}")
    for g in kill_gates["gates"]:
        if g["status"] == "pass":
            continue
        msg = f"kill-gate {g['id']} ({g['name']}): {g['status']}"
        (r.advisories if g["id"] in ADVISORY_GATES else r.problems).append(msg)
    if draft_text is not None:
        bindings = [b for b in bind_markers(draft_text, registry, kill_gates) if b.kind != "header"]
        r.n_markers = len(bindings)
        r.n_bound = sum(1 for b in bindings if b.ok)
        for b in bindings:
            r.problems.extend(f"draft marker: {p}" for p in b.problems)
        for ln, m in find_open_markers(draft_text):
            r.problems.append(f"owner decision open in the draft at line {ln}: {m}")
    if spec_status == "FROZEN" and r.problems:
        r.problems.insert(0, "SPEC_STATUS is FROZEN but markers remain — inconsistent")
    return r


def check_repo(registry_path: Path = REGISTRY_PATH, kill_gates_path: Path = KILL_GATES_PATH,
               draft_path: Path | None = DRAFT_PATH) -> FreezeReport:
    from tripstate.version import SPEC_STATUS

    draft = draft_path.read_text(encoding="utf-8") if draft_path and draft_path.exists() else None
    return check_freeze(load_yaml(registry_path), load_yaml(kill_gates_path), draft, SPEC_STATUS)


def render(report: FreezeReport, spec_status: str) -> str:
    lines = [f"spec status: {spec_status}"]
    lines += [f"ADVISORY  {a}" for a in report.advisories]
    if report.n_markers:
        lines.append(f"draft [EG] markers: {report.n_markers} ({report.n_bound} bound to registry/kill-gates)")
    if report.problems:
        lines.append(f"FREEZE BLOCKED — {len(report.problems)} item(s):")
        lines += [f"  - {p}" for p in report.problems]
    else:
        lines.append("FREEZE ALLOWED: all EG entries instantiated, kill-gates pass, every draft marker bound, no open owner decisions.")
    return "\n".join(lines)
