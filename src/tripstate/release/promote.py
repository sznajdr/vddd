"""The D-36 promotion: SPEC-2.0.0-draft.md → SPEC-2.0.0.md (FROZEN) in one deterministic transform.

Inputs are texts and registries, outputs are texts; the CLI (tools/promote_draft.py) decides whether they land
in the repository (real run) or in a scratch directory with diffs (dry run). Steps, in order (handoff §2 A5):
  1. refuse unless the freeze check passes on the given registry + kill-gates + draft (EG, KG-1…KG-4, every
     marker bound, no `[OPEN]` owner decision left);
  2. header: Status → FROZEN, promotion rule → freeze record, version line;
  3. §1: D-26…D-36 rows appended verbatim from the decision log, pending paragraph replaced;
  4. every `[EG]` marker replaced by the instantiated value (provisional kept only in the changelog row);
  5. §7.1 machine-copy pointer → the frozen threshold set; changelog row; end line;
  6. decision log: D-26…D-36 move from Pending to Closed;
  7. frozen threshold set from TS-0.0.0-provisional with registry values, eg: false, search_provenance: freeze;
  8. version.py bump (real run only decides whether to write it).
Every anchor must match exactly once, else the promotion refuses: a silent partial promotion is worse than none.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from tripstate.release.freeze import check_freeze
from tripstate.release.markers import (
    Substitution,
    format_value,
    strip_open_markers,
    substitute_markers,
)

PENDING_IDS = tuple(f"D-{i}" for i in range(26, 37))
TS_LINE_RE = re.compile(r'^(?P<ind>\s+)(?P<key>[A-Za-z_][A-Za-z0-9_]*): \{value: (?P<val>[^,}]+?)(?P<eg>, eg: (?:true|false))?(?P<rest>(?:, [a-z_]+: (?:"[^"]*"|[^,}]+))*)\}\s*$')


class PromotionRefused(Exception):
    def __init__(self, reasons: list[str]):
        super().__init__("; ".join(reasons))
        self.reasons = reasons


@dataclass
class PromotionInputs:
    draft_text: str
    decision_log_text: str
    ts_text: str
    version_py_text: str
    registry: dict
    kill_gates: dict
    date: str
    spec_version: str = "2.0.0"
    draft_version: str = "2.0.0-draft"
    ts_version: str = "TS-2.0.0-frozen"
    ts_source_version: str = "TS-0.0.0-provisional"
    strip_open: bool = False      # dry-run simulation of the owner's [OPEN] resolutions; never in a real run


@dataclass
class PromotionOutputs:
    frozen_spec: str
    decision_log: str
    frozen_ts: str
    version_py: str
    substitutions: list[Substitution] = field(default_factory=list)
    ts_changes: list[tuple[str, str, str]] = field(default_factory=list)   # (key, provisional, frozen)
    changelog_row: str = ""
    freeze_record: str = ""
    report_md: str = ""


def _replace_once(text: str, pattern: str, repl, what: str, flags: int = re.MULTILINE) -> str:
    n = len(re.findall(pattern, text, flags))
    if n != 1:
        raise PromotionRefused([f"{what}: expected exactly one match for {pattern!r}, found {n}"])
    return re.sub(pattern, repl, text, count=1, flags=flags)


def pending_rows(decision_log_text: str) -> list[str]:
    """The D-26…D-36 table rows of the decision log's Pending section, verbatim."""
    m = re.search(r"^## Pending[^\n]*\n(?P<body>.*?)(?=^## |\Z)", decision_log_text, re.MULTILINE | re.DOTALL)
    if not m:
        raise PromotionRefused(["decision log: no '## Pending' section"])
    rows = [ln for ln in m.group("body").splitlines() if re.match(r"^\| D-\d{2} \|", ln)]
    ids = [ln.split("|")[1].strip() for ln in rows]
    if tuple(ids) != PENDING_IDS:
        raise PromotionRefused([f"decision log pending rows are {ids}, expected {list(PENDING_IDS)}"])
    return rows


def _fmt_measure(g: dict) -> str:
    m = g.get("measured")
    return "—" if m is None else (f"{m:.3g}" if isinstance(m, float) else str(m))


def freeze_record_line(inp: PromotionInputs) -> str:
    entries = inp.registry["entries"]
    dates = sorted({str(e.get("date")) for e in entries if e.get("date")})
    gates = {g["id"]: g for g in inp.kill_gates["gates"]}
    spec_gates = ", ".join(f"{k} {_fmt_measure(gates[k])}" for k in ("KG-1", "KG-2", "KG-3", "KG-4") if k in gates)
    ev = sorted({str(gates[k].get("evidence")) for k in ("KG-1", "KG-2", "KG-3", "KG-4") if k in gates and gates[k].get("evidence")})
    kg5 = gates.get("KG-5", {}).get("status", "absent")
    return (f"**Freeze record (D-36):** promoted from `SPEC-{inp.draft_version}.md` on {inp.date} by `tools/promote_draft.py`. "
            f"Evidence: `registers/evidence_gated.yaml` registry_version {inp.registry.get('registry_version')} "
            f"({len(entries)} entries instantiated, dated {dates[0]}…{dates[-1]}); kill-gates KG-1…KG-4 `pass` ({spec_gates}; "
            f"evidence: {'; '.join(ev) or 'see registers/kill_gates.yaml'}); KG-5 {kg5} (advisory, project gate); "
            f"`tools/freeze_check.py` exit 0.")


def frozen_spec(inp: PromotionInputs) -> tuple[str, list[Substitution], str, str]:
    text = strip_open_markers(inp.draft_text) if inp.strip_open else inp.draft_text
    rep = check_freeze(inp.registry, inp.kill_gates, text, "DRAFT")
    if not rep.allowed:
        raise PromotionRefused(rep.problems)
    dv, sv = re.escape(inp.draft_version), inp.spec_version
    record = freeze_record_line(inp)
    # 2. header
    text = _replace_once(text, rf"^# SPEC-{dv} — ", f"# SPEC-{sv} — ", "title")
    text = _replace_once(text, r"^\*\*Status:\*\* DRAFT \(D-36\)\..*$",
                         "**Status:** FROZEN (normative). Changes require a version bump per §14.", "status line")
    text = _replace_once(text, r"^\*\*Promotion rule \(D-36\):\*\*.*$", lambda _m: record, "promotion rule")
    text = _replace_once(text, rf"^\*\*Version:\*\* {dv} — ", f"**Version:** {sv} — frozen from {inp.draft_version}: ", "version line")
    # 3. §1 rows + pending paragraph
    rows = pending_rows(inp.decision_log_text)
    text = _replace_once(text, r"^(\| D-25 \|.*)$", lambda m: m.group(1) + "\n" + "\n".join(rows), "D-25 row")
    text = _replace_once(text, r"^\*\*Pending at freeze \(D-36\):\*\*.*$",
                         f"**Appended at freeze (D-36):** D-26…D-36 above were appended verbatim from `decisions/DECISION-LOG.md` "
                         f"by the promotion commit of {inp.date}; they are closed decisions and MUST NOT be reopened by agents.",
                         "pending paragraph")
    # 4. markers
    text, subs, problems = substitute_markers(text, inp.registry, inp.kill_gates)
    if problems:
        raise PromotionRefused(problems)
    # 5. machine copy, changelog row, end line
    text = _replace_once(text, r"`config/thresholds/TS-0\.0\.0-provisional\.yaml`",
                         f"`config/thresholds/{inp.ts_version}.yaml` (frozen from `TS-0.0.0-provisional.yaml` at promotion)", "§7.1 machine copy")
    row = changelog_row(inp, subs)
    text = _replace_once(text, rf"^(\| {dv} \| .*)$", lambda m: m.group(1) + "\n" + row, "changelog draft row")
    text = _replace_once(text, rf"^\*End of SPEC-{dv}\.\*$", f"*End of SPEC-{sv}.*", "end line")
    leftovers = [ln for ln, line in enumerate(text.splitlines(), 1) if "`[EG" in line or "`[OPEN" in line]
    if leftovers:
        raise PromotionRefused([f"markers remain after substitution at lines {leftovers}"])
    if text.count("**Status:** FROZEN") != 1:
        raise PromotionRefused(["frozen file must carry exactly one FROZEN status line"])
    return text, subs, row, record


def _ts_keys_in_registry(inp: PromotionInputs) -> dict[str, dict]:
    return {e["key"]: e for e in inp.registry["entries"] if e.get("instantiated")}


def changelog_row(inp: PromotionInputs, subs: list[Substitution]) -> str:
    reg = _ts_keys_in_registry(inp)
    ts_keys = {m.group("key"): m.group("val") for m in (TS_LINE_RE.match(ln) for ln in inp.ts_text.splitlines()) if m}
    changed, same, named = [], [], []
    for k, e in reg.items():
        if k in ts_keys:
            prov, val = e.get("provisional"), e.get("value")
            if prov is not None and abs(float(val) - float(prov)) > 1e-9:
                changed.append(f"`{k}` {format_value(val, str(prov))} (provisional was {prov})")
            else:
                same.append(f"`{k}`")
        else:
            named.append(f"`{k}` = {e.get('value')}")
    gates = {g["id"]: g for g in inp.kill_gates["gates"]}
    kg5 = gates.get("KG-5", {}).get("status", "absent")
    return (f"| {inp.spec_version} | {inp.date} | FROZEN: promoted from {inp.draft_version} by `tools/promote_draft.py` (D-36). "
            f"EG registry v{inp.registry.get('registry_version')} instantiated from the OD-1x sheets and the 5-race pilot — "
            f"frozen values: {', '.join(changed) or 'none changed'}; unchanged at provisional: {', '.join(same) or 'none'}; "
            f"named checks: {', '.join(named) or 'none'}. Kill-gates KG-1…KG-4 pass; KG-5 {kg5}. D-26…D-36 appended to §1; "
            f"EG markers stripped; open owner decisions resolved before promotion. Threshold set `{inp.ts_version}` "
            f"(calibrated: false; §7 calibration pending). Headline evaluation not yet run (the first held-out evaluation "
            f"appends its own entry). No artifact migration (none exist under {inp.draft_version}). |")


def frozen_decision_log(inp: PromotionInputs) -> str:
    rows = pending_rows(inp.decision_log_text)
    m = re.search(r"^## Pending[^\n]*\n.*?(?=^## |\Z)", inp.decision_log_text, re.MULTILINE | re.DOTALL)
    assert m is not None
    closed = (f"## Closed (SPEC-{inp.spec_version} §1) — D-26…D-36\n\n"
              f"Appended verbatim to §1 of `spec/SPEC-{inp.spec_version}.md` at the freeze ({inp.date}). Full text there.\n\n"
              "| ID | Decision | Rationale |\n|---|---|---|\n" + "\n".join(rows) + "\n\n"
              "## Pending\n\n"
              f"None — the {inp.spec_version} line is frozen ({inp.date}). The next decision is D-37 and follows §14 "
              "(append-only; reopening = MAJOR bump + owner sign-off).\n\n")
    return inp.decision_log_text[: m.start()] + closed + inp.decision_log_text[m.end():]


def frozen_threshold_set(inp: PromotionInputs) -> tuple[str, list[tuple[str, str, str]]]:
    reg = _ts_keys_in_registry(inp)
    out: list[str] = []
    changes: list[tuple[str, str, str]] = []
    problems: list[str] = []
    header_done = False
    for ln in inp.ts_text.splitlines():
        if not header_done:
            if ln.startswith("#"):
                continue
            header_done = True
            out += [f"# Threshold set {inp.ts_version} — SPEC-{inp.spec_version} §7.1 (FROZEN values, NOT calibrated).",
                    f"# Written by tools/promote_draft.py on {inp.date} from {inp.ts_source_version}: every evidence-gated value replaced by",
                    "# its instantiated registry value (spec/registers/evidence_gated.yaml); eg flags cleared. §7.2 calibration",
                    "# produces the next set (TS-2.x, calibrated: true, search_provenance recorded).",
                    "# Modules read values through tripstate.config.ThresholdSet; never import numbers from here directly."]
        if ln.startswith("threshold_set_version:"):
            out.append(f"threshold_set_version: {inp.ts_version}")
            continue
        if ln.startswith("spec_version:"):
            out.append(f"spec_version: {inp.spec_version}")
            continue
        if ln.startswith("search_provenance:"):
            out.append("search_provenance: freeze")
            out.append("freeze_record:")
            out.append(f"  date: {inp.date}")
            out.append(f"  promoted_from: {inp.ts_source_version}")
            out.append(f"  registry_version: {inp.registry.get('registry_version')}")
            continue
        m = TS_LINE_RE.match(ln)
        if m:
            key, val, eg, rest, ind = m.group("key"), m.group("val"), m.group("eg"), m.group("rest"), m.group("ind")
            if key in reg:
                new = format_value(reg[key]["value"], val)
                if new != val:
                    changes.append((key, val, new))
                out.append(f"{ind}{key}: {{value: {new}, eg: false{rest}}}")
                continue
            if eg and "true" in eg:
                problems.append(f"{key} is flagged eg: true but has no instantiated registry entry")
            out.append(ln)
            continue
        out.append(ln)
    if problems:
        raise PromotionRefused(problems)
    text = "\n".join(out) + "\n"
    if "eg: true" in text:
        raise PromotionRefused(["frozen threshold set still carries eg: true"])
    return text, changes


def bumped_version_py(inp: PromotionInputs) -> str:
    t = _replace_once(inp.version_py_text, rf'^SPEC_VERSION = "{re.escape(inp.draft_version)}"$',
                      f'SPEC_VERSION = "{inp.spec_version}"', "version.py SPEC_VERSION")
    t = _replace_once(t, r'^SPEC_STATUS = "DRAFT".*$',
                      f'SPEC_STATUS = "FROZEN"  # promoted by tools/promote_draft.py on {inp.date} (D-36)', "version.py SPEC_STATUS")
    return t


def promote(inp: PromotionInputs) -> PromotionOutputs:
    spec, subs, row, record = frozen_spec(inp)
    log = frozen_decision_log(inp)
    ts, ts_changes = frozen_threshold_set(inp)
    vpy = bumped_version_py(inp)
    out = PromotionOutputs(spec, log, ts, vpy, subs, ts_changes, row, record)
    out.report_md = report(inp, out)
    return out


def report(inp: PromotionInputs, out: PromotionOutputs) -> str:
    lines = [f"# Promotion report — {inp.draft_version} → {inp.spec_version} ({inp.date})", "",
             f"Mode: {'DRY RUN (synthetic registry; [OPEN] markers stripped for the simulation)' if inp.strip_open else 'promotion'}", "",
             "## Freeze record", "", out.freeze_record, "", "## Marker substitutions (spec line, key, provisional → frozen)", "",
             "| line | key | kind | provisional | frozen |", "|---|---|---|---|---|"]
    lines += [f"| {s.line_no} | `{s.key}` | {s.kind} | {s.provisional} | {s.frozen} |" for s in out.substitutions]
    lines += ["", "## Threshold set changes (TS-0.0.0-provisional → frozen)", "", "| key | provisional | frozen |", "|---|---|---|"]
    lines += [f"| `{k}` | {a} | {b} |" for k, a, b in out.ts_changes] or ["| (none) | | |"]
    lines += ["", "## Changelog row", "", out.changelog_row, ""]
    return "\n".join(lines)


def unified_diff(old: str, new: str, name: str) -> str:
    return "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{name}", f"b/{name}"))
