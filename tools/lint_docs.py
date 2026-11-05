#!/usr/bin/env python3
"""Documentation hygiene (keeps the repository map honest; runs in `make lint-docs` and CI).

Checks:
  1. every repository path named in a CURRENT-STATE document (README.md, CLAUDE.md, STATUS.md, ROADMAP.md, the
     index pages, protocols, module READMEs) exists — placeholders (<…>, *, {…}) and data/ paths are skipped;
  2. every tools/*.py is listed in tools/README.md;
  3. every package under src/tripstate with an __init__.py has a README.md;
  4. every `make <target>` in a code span or code block of a current-state document exists in the Makefile;
  5. no current-state document still says a backlog item is pending when BACKLOG.md marks it ✅ (spot check on IDs).
Plans and history (BACKLOG, HANDOFF, research, decisions, spec/RECON) may name future files and are not path-checked.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT_STATE = ["README.md", "CLAUDE.md", "STATUS.md", "ROADMAP.md", "docs/README.md", "docs/ARCHITECTURE.md", "tools/README.md",
                 "protocols/README.md", "spec/README.md", "src/tripstate/README.md", "data/README.md"]
CURRENT_STATE += [str(p.relative_to(ROOT)) for p in sorted(ROOT.glob("protocols/**/*.md"))]
CURRENT_STATE += [str(p.relative_to(ROOT)) for p in sorted(ROOT.glob("src/tripstate/*/README.md"))]
CURRENT_STATE += [str(p.relative_to(ROOT)) for p in sorted(ROOT.glob("tests/fixtures/*/README.md"))]
PATH_RE = re.compile(r"`((?:tools|src|tests|protocols|config|spec|docs)/[A-Za-z0-9_./\-]+)`")
MAKE_RE = re.compile(r"(?:`|^)make ([a-z][a-z0-9-]+)", re.MULTILINE)   # code spans and code-block lines only, not prose
PLAN_DOCS = {"docs/BACKLOG.md", "docs/HANDOFF-NEXT-SESSION.md"}                   # may name targets that do not exist yet


def check_paths() -> list[str]:
    problems = []
    for rel in dict.fromkeys(CURRENT_STATE):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in PATH_RE.finditer(text):
            ref = m.group(1).rstrip(".,;:")
            if any(c in ref for c in "<>*{}") or ref.endswith("/"):
                continue
            if not (ROOT / ref).exists():
                problems.append(f"{rel}: references missing path `{ref}`")
    return problems


def check_tools_index() -> list[str]:
    index = (ROOT / "tools" / "README.md").read_text(encoding="utf-8")
    return [f"tools/README.md: {p.name} is not listed" for p in sorted(ROOT.glob("tools/*.py")) if f"`{p.name}`" not in index]


def check_package_readmes() -> list[str]:
    out = []
    for d in sorted(ROOT.glob("src/tripstate/*/")):
        if (d / "__init__.py").exists() and not (d / "README.md").exists():
            out.append(f"{d.relative_to(ROOT)}: package without README.md")
    return out


def makefile_targets() -> set[str]:
    return set(re.findall(r"^([a-z][a-z0-9-]+):", (ROOT / "Makefile").read_text(encoding="utf-8"), re.MULTILINE))


def check_make_targets() -> list[str]:
    targets = makefile_targets()
    problems = []
    for p in sorted(ROOT.glob("**/*.md")):
        rel = p.relative_to(ROOT).as_posix()
        if any(part in {".git", "data", "__pycache__", ".pytest_cache", ".ruff_cache", "research", "decisions"} for part in p.parts) or rel in PLAN_DOCS:
            continue
        for m in MAKE_RE.finditer(p.read_text(encoding="utf-8")):
            t = m.group(1)
            if t not in targets:
                problems.append(f"{rel}: `make {t}` is not a Makefile target")
    return problems


def check_backlog_consistency() -> list[str]:
    backlog = (ROOT / "docs" / "BACKLOG.md").read_text(encoding="utf-8")
    done = set(re.findall(r"^\| ([A-D]\d) ✅ \|", backlog, re.MULTILINE))
    problems = []
    handoff = (ROOT / "docs" / "HANDOFF-NEXT-SESSION.md").read_text(encoding="utf-8")
    for item in sorted(done):
        if re.search(rf"^\d+\. {item}:", handoff, re.MULTILINE):
            problems.append(f"docs/HANDOFF-NEXT-SESSION.md: lists {item} as a next task but BACKLOG.md marks it done")
    return problems


def main() -> int:
    problems = check_paths() + check_tools_index() + check_package_readmes() + check_make_targets() + check_backlog_consistency()
    for p in problems:
        print(p)
    print("lint-docs:", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
