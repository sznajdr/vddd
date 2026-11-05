"""`[EG: …]` marker binding (SPEC-2.0.0-draft header, D-36 promotion rule (1)).

Every evidence-gated marker in the draft must bind to exactly the registry entries (or kill-gates) that
instantiate it; the promotion substitutes the instantiated value for the provisional number written next to
the marker and strips the marker. A marker that binds to nothing is a defect of the draft/registry pair and
blocks the freeze — a number without evidence stays marked, never silently becomes fact (prime directive).

Binding rules, in order:
  1. a context rule (the few markers whose line carries no threshold key: kill-gate rows, "cap 8 min", …);
  2. an explicit `→ key` inside the marker text;
  3. the nearest preceding code span(s) on the same line that contain registry keys (spans joined by " / "
     form one group; `<start_type>` templates expand to volte/autostart).
The numeric token(s) written immediately before the marker must equal the registry's `provisional` values
(spec and registry must agree before either is trusted).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

MARKER_RE = re.compile(r"`\[EG(?::\s*(?P<text>[^\]]*))?\]`")
OPEN_RE = re.compile(r"`\[OPEN(?::\s*(?P<text>[^\]]*))?\]`")
CODE_SPAN_RE = re.compile(r"`([^`]+)`")
# numbers written just before a marker: "0.8 SW **", "0.0 / 0.0 ", "8 min ", "**≤ 5 minutes** ", "(default 3 "
NUMS_BEFORE_RE = re.compile(r"(?P<nums>\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)*)\s*(?:SW|SL|min|minutes|s|%)?\*{0,2}\s*$")
ARROW_KEY_RE = re.compile(r"→\s*([A-Za-z_][A-Za-z0-9_]*)")
START_TYPES = ("volte", "autostart")
ANCHOR_KEYS = ("anchor_offset_volte_s", "anchor_offset_autostart_s", "anchor_tol_volte_s", "anchor_tol_autostart_s")
SPEC_KILL_GATES = ("KG-1", "KG-2", "KG-3", "KG-4")
HEADER_PREFIXES = ("**Status:**", "**Promotion rule")


@dataclass(frozen=True)
class ContextRule:
    pattern: str                      # regex tested against the whole line
    kind: str                         # registry | kill_gate | kill_gates_all | meta
    keys: tuple[str, ...]
    replacement: str | None = None    # text that replaces the marker when no number precedes it


CONTEXT_RULES: tuple[ContextRule, ...] = (
    ContextRule(r"Instantiating every `\[EG\]` value", "meta", (), "evidence-gated"),
    ContextRule(r"^### 0\.4 Kill-gates", "kill_gates_all", SPEC_KILL_GATES, "frozen (`registers/kill_gates.yaml`)"),
    ContextRule(r"^\| KG-1 \|", "kill_gate", ("KG-1",)),
    ContextRule(r"cap \d+(?:\.\d+)? min `\[EG\]`", "registry", ("human_budget_cap_min",)),
    ContextRule(r"all four keys `\[EG", "registry", ANCHOR_KEYS, "frozen"),
)


@dataclass
class Binding:
    line_no: int                       # 1-based
    marker: str                        # the full marker text as written
    kind: str                          # registry | kill_gate | kill_gates_all | meta | header | unbound
    keys: list[str] = field(default_factory=list)
    nums: list[str] = field(default_factory=list)      # numeric tokens written before the marker, in order
    nums_span: tuple[int, int] | None = None            # column span of those tokens in the line
    replacement: str | None = None                      # replaces the marker when nums is empty
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


def _registry_keys(registry: dict) -> set[str]:
    return {e["key"] for e in registry.get("entries", [])}


def _keys_in_span(span: str, keys: set[str]) -> list[str]:
    found: list[tuple[int, str]] = []
    for k in keys:
        for m in re.finditer(rf"(?<![A-Za-z0-9_]){re.escape(k)}(?![A-Za-z0-9_])", span):
            found.append((m.start(), k))
    if "<start_type>" in span:
        for m in re.finditer(r"([A-Za-z_]+)<start_type>([A-Za-z0-9_]*)", span):
            for st in START_TYPES:
                k = f"{m.group(1)}{st}{m.group(2)}"
                if k in keys:
                    found.append((m.start(), k))
    seen: list[str] = []
    for _, k in sorted(found):
        if k not in seen:
            seen.append(k)
    return seen


def _nearest_key_group(before: str, keys: set[str]) -> list[str]:
    """Registry keys in the nearest preceding code span(s); spans joined only by ' / ' form one group."""
    spans = list(CODE_SPAN_RE.finditer(before))
    group: list[str] = []
    i = len(spans) - 1
    while i >= 0:
        ks = _keys_in_span(spans[i].group(1), keys)
        if ks:
            group = ks + group
            if i > 0 and re.fullmatch(r"\s*/\s*", before[spans[i - 1].end():spans[i].start()]):
                i -= 1
                continue
            break
        if group:
            break
        i -= 1
    return group


def _num(x: str) -> float:
    return float(x)


def bind_markers(text: str, registry: dict, kill_gates: dict) -> list[Binding]:
    """One Binding per `[EG]` marker occurrence in `text`, header lines included (kind='header')."""
    keys = _registry_keys(registry)
    reg_by = {e["key"]: e for e in registry.get("entries", [])}
    gates_by = {g["id"]: g for g in kill_gates.get("gates", [])}
    out: list[Binding] = []
    for ln, line in enumerate(text.splitlines(), start=1):
        for m in MARKER_RE.finditer(line):
            b = Binding(ln, m.group(0), "unbound")
            if line.startswith(HEADER_PREFIXES):
                b.kind = "header"
                out.append(b)
                continue
            before = line[: m.start()]
            rule = next((r for r in CONTEXT_RULES if re.search(r.pattern, line)), None)
            if rule is not None:
                b.kind, b.keys, b.replacement = rule.kind, list(rule.keys), rule.replacement
            else:
                arrow = ARROW_KEY_RE.search(m.group("text") or "")
                if arrow:
                    b.kind, b.keys = "registry", [arrow.group(1)]
                else:
                    grp = _nearest_key_group(before, keys)
                    if grp:
                        b.kind, b.keys = "registry", grp
            if b.kind == "unbound":
                b.problems.append(f"line {ln}: marker {b.marker} binds to no registry entry or kill-gate: {line.strip()[:100]}")
                out.append(b)
                continue
            if b.kind == "registry":
                for k in b.keys:
                    if k not in reg_by:
                        b.problems.append(f"line {ln}: key {k} is not in the EG registry")
            if b.kind in ("kill_gate", "kill_gates_all"):
                for k in b.keys:
                    if k not in gates_by:
                        b.problems.append(f"line {ln}: kill-gate {k} is not in kill_gates.yaml")
            nm = NUMS_BEFORE_RE.search(before)
            if nm and b.kind in ("registry", "kill_gate"):
                b.nums = [s.strip() for s in nm.group("nums").split("/")]
                b.nums_span = (nm.start("nums"), nm.end("nums"))
                if len(b.nums) != len(b.keys):
                    b.problems.append(f"line {ln}: {len(b.nums)} number(s) written for {len(b.keys)} key(s) {b.keys}")
                else:
                    for k, s in zip(b.keys, b.nums):
                        prov = provisional_of(k, b.kind, reg_by, gates_by)
                        if prov is None:
                            b.problems.append(f"line {ln}: {k} has no provisional value to check against")
                        elif abs(_num(s) - float(prov)) > 1e-9:
                            b.problems.append(f"line {ln}: spec writes {s} for {k} but the registry provisional is {prov}")
            out.append(b)
    return out


def provisional_of(key: str, kind: str, reg_by: dict, gates_by: dict):
    if kind == "registry":
        return reg_by.get(key, {}).get("provisional")
    g = gates_by.get(key, {})
    for f in ("threshold_min", "threshold", "threshold_factor"):
        if g.get(f) is not None:
            return g[f]
    return None


def instantiated_of(key: str, kind: str, reg_by: dict, gates_by: dict):
    """The frozen value: registry `value` for an instantiated entry, the gate threshold for a passing gate."""
    if kind == "registry":
        e = reg_by.get(key)
        if e is None or not e.get("instantiated") or e.get("value") is None:
            return None
        return e["value"]
    g = gates_by.get(key)
    if g is None or g.get("status") != "pass":
        return None
    return provisional_of(key, kind, reg_by, gates_by)


def format_value(value, like: str) -> str:
    """Format a frozen value in the style of the provisional text it replaces (same minimum decimals)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"non-numeric frozen value {value!r}")
    dec = len(like.split(".")[1]) if "." in like else 0
    v = float(value)
    if isinstance(value, int) and dec == 0:
        return str(value)
    for d in range(dec, 7):
        if abs(round(v, d) - v) < 1e-9:
            return f"{v:.{d}f}"
    return repr(v)


def find_open_markers(text: str) -> list[tuple[int, str]]:
    return [(ln, m.group(0)) for ln, line in enumerate(text.splitlines(), start=1) for m in OPEN_RE.finditer(line)]


def strip_open_markers(text: str) -> str:
    """Dry-run simulation only: remove `[OPEN…]` markers (and a dangling ', ' before a bare one)."""
    text = re.sub(r",\s*`\[OPEN\]`", "", text)
    text = re.sub(r"`\[OPEN(?::[^\]]*)?\]`\s?", "", text)
    return text


@dataclass
class Substitution:
    line_no: int
    key: str
    kind: str
    provisional: str
    frozen: str


def substitute_markers(text: str, registry: dict, kill_gates: dict) -> tuple[str, list[Substitution], list[str]]:
    """Replace every bound marker by its frozen value. Header-line markers are left for the header rewrite.
    Returns (new_text, substitutions, problems). Nothing is written when problems remain."""
    reg_by = {e["key"]: e for e in registry.get("entries", [])}
    gates_by = {g["id"]: g for g in kill_gates.get("gates", [])}
    bindings = bind_markers(text, registry, kill_gates)
    problems = [p for b in bindings for p in b.problems]
    subs: list[Substitution] = []
    lines = text.splitlines(keepends=True)
    by_line: dict[int, list[Binding]] = {}
    for b in bindings:
        by_line.setdefault(b.line_no, []).append(b)
    for ln, bs in by_line.items():
        line = lines[ln - 1]
        # process right-to-left so earlier column spans stay valid
        for b in sorted(bs, key=lambda x: line.rfind(x.marker), reverse=True):
            if b.kind == "header" or not b.ok:
                continue
            pos = line.rfind(b.marker)
            if b.nums:
                values = []
                for k, s in zip(b.keys, b.nums):
                    v = instantiated_of(k, b.kind, reg_by, gates_by)
                    if v is None:
                        problems.append(f"line {ln}: {k} is not instantiated (or its kill-gate does not pass)")
                        continue
                    fv = format_value(v, s)
                    values.append(fv)
                    subs.append(Substitution(ln, k, b.kind, s, fv))
                if len(values) != len(b.keys):
                    continue
                a, z = b.nums_span  # type: ignore[misc]
                line = line[:a] + " / ".join(values) + line[z:pos].rstrip(" ") + line[pos + len(b.marker):]
            else:
                for k in b.keys:
                    if instantiated_of(k, b.kind, reg_by, gates_by) is None and b.kind != "meta":
                        problems.append(f"line {ln}: {k} is not instantiated (or its kill-gate does not pass)")
                if b.replacement is not None:
                    line = line[:pos] + b.replacement + line[pos + len(b.marker):]
                else:
                    head = line[:pos].rstrip(" ")
                    line = head + line[pos + len(b.marker):]
        lines[ln - 1] = line
    return "".join(lines), subs, problems
