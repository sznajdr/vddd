"""Notule parser (SPEC-2.0.0-draft §11.3): clause-level candidate sets, phases, negation / quotation /
third-party scope, break events, reserved and excluded families. Never fabricates fractions (rule 4)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from tripstate.textparse.lexicon import (
    FAMILIES,
    PHASE_FAMILIES,
    candidates_for,
    merge_assertions,
)
from tripstate.textparse.normalize import normalize

MAPPING_RULE_VERSION = "lex-2.0.0-draft.1"
_CLAUSE_SPLIT = re.compile(r"[.;,:]|\b(?:puis|avant de|avant d'|mais|et|ou|pour)\b")
_NEG = re.compile(r"(?:\bne\s+|\bn')(?:[\w']+\s+){0,3}?(?:pas|jamais|plus|guere|point)\b")
_OTHER_SUBJECT = re.compile(r"^\s*(?:le|la|l')?\s*(?:n°|no|numero|num)?\s*(\d{1,2})\b|^\s*le (?:favori|\d{1,2})\b")
_QUOTE = re.compile(r'"[^"]*"')


@dataclass
class Hit:
    family: str
    target: str
    phrase: str
    clause_idx: int
    negated: bool = False
    scope: str = "subject"     # subject | other | quoted


@dataclass
class ParseResult:
    race_id: str
    saddle_no: int
    source_text_id: str
    segments: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    hits: list[Hit] = field(default_factory=list)
    clauses: list[str] = field(default_factory=list)

    def families(self) -> set[str]:
        return {h.family for h in self.hits if not h.negated and h.scope == "subject"}


def split_clauses(text_norm: str) -> list[str]:
    parts = [p.strip() for p in _CLAUSE_SPLIT.split(text_norm)]
    return [p for p in parts if p]


def _phase_of(clause: str) -> tuple[str, str | None]:
    for pat, phase, _ in PHASE_FAMILIES:
        m = re.search(pat, clause)
        if m:
            return phase, m.group(0)
    return "unknown", None


def _negated(clause: str, start: int) -> bool:
    m = _NEG.search(clause[: start + 1])
    return bool(m) and (start - m.start()) < 40


def _row(race_id: str, saddle_no: int, source_text_id: str, phase: str, phrase: str, state: str | None,
         candidates: list[str], status: str, conf: float | None, *, kind: str = "base", covered=None,
         lead=None, lead_amb=None, tier_attr=None, end_attr=None) -> dict:
    return {
        "race_id": race_id, "saddle_no": saddle_no, "state_kind": kind, "state": state, "covered": covered,
        "lead_uncovered_outside": lead, "lead_uncovered_outside_ambiguous": lead_amb, "tier_attr": tier_attr,
        "end_attr": end_attr, "method": "text_parse", "t_start_frac": None, "t_end_frac": None, "confidence": None,
        "visibility": "visible", "start_truncated": False, "end_truncated": False, "charter_minutes": None,
        "phase": phase, "source_text_id": source_text_id, "source_phrase": phrase,
        "mapping_rule_version": MAPPING_RULE_VERSION, "mapping_confidence": conf, "mapping_status": status,
        "candidate_states": candidates,
    }


def parse_notule(text: str, race_id: str, saddle_no: int, source_text_id: str = "") -> ParseResult:
    res = ParseResult(race_id, saddle_no, source_text_id)
    norm = normalize(text)
    quoted_spans = [(m.start(), m.end()) for m in _QUOTE.finditer(norm)]
    res.clauses = split_clauses(norm)
    offset = 0
    for ci, clause in enumerate(res.clauses):
        cstart = norm.find(clause, offset)
        offset = cstart + len(clause) if cstart >= 0 else offset
        clause_scope = "other" if _OTHER_SUBJECT.search(clause) and not re.match(r"^\s*(?:le|la)?\s*\d{1,2}e\b", clause) else "subject"
        phase, _phase_phrase = _phase_of(clause)
        asserted: list[dict] = []
        phrases: list[str] = []
        lead: bool | None = None
        tier_attr = None
        excluded_here = False
        for fam in FAMILIES:
            for m in fam.regex.finditer(clause):
                neg = _negated(clause, m.start())
                pos = cstart + m.start() if cstart >= 0 else -1
                scope = "quoted" if any(a <= pos < b for a, b in quoted_spans) else clause_scope
                res.hits.append(Hit(fam.id, fam.target, m.group(0), ci, neg, scope))
                if neg or scope != "subject":
                    continue
                if fam.target == "EXCLUDED":
                    excluded_here = True
                elif fam.target == "PROXIMITY":
                    pass
                elif fam.target.startswith("OVERLAY:"):
                    end = fam.end_attr
                    if end is None and any(h.target == "LEADER" and h.clause_idx <= ci and not h.negated and h.scope == "subject" for h in res.hits):
                        end = "front"
                    res.segments.append(_row(race_id, saddle_no, source_text_id, phase, m.group(0), "DETACHED", ["DETACHED"],
                                             "resolved" if end else "ambiguous", (0.9 if end else None) if phase != "unknown" else (0.7 if end else None),
                                             kind="overlay", end_attr=end))
                elif fam.target.startswith("EVENT:"):
                    rec = fam.recovered
                    if any(e["_clause"] == ci for e in res.events):
                        if rec and not any(e["recovered"] for e in res.events if e["_clause"] == ci):
                            for e in res.events:
                                if e["_clause"] == ci:
                                    e["recovered"] = True
                        continue
                    res.events.append({"race_id": race_id, "saddle_no": saddle_no, "type": "BREAK", "t_start_frac": None, "t_end_frac": None,
                                       "positions_lost": None, "positions_lost_basis_n": None, "recovered": rec, "method": "text_parse",
                                       "review_status": "pending", "human_confirmed": False, "phase": phase, "source_phrase": m.group(0),
                                       "source_text_id": source_text_id, "mapping_rule_version": MAPPING_RULE_VERSION, "_clause": ci})
                elif fam.target.startswith("RESERVED:"):
                    pass
                else:
                    asserted.append(fam.asserts)
                    phrases.append(m.group(0))
                    if fam.lead:
                        lead = True
                    if fam.tier_attr:
                        tier_attr = fam.tier_attr
        if not asserted:
            continue
        merged = merge_assertions(asserted)
        if merged is None:
            res.segments.append(_row(race_id, saddle_no, source_text_id, phase, " / ".join(phrases), None, [], "contradictory", None))
            continue
        cands = candidates_for(merged)
        if len(cands) == 1:
            st = cands[0]
            specificity = 1.0 if len(asserted) == 1 else 0.8
            conf = specificity * (1.0 if phase != "unknown" else 0.8) * (0.7 if excluded_here else 1.0)
            covered = merged.get("covered") if isinstance(merged.get("covered"), bool) else None
            res.segments.append(_row(race_id, saddle_no, source_text_id, phase, " / ".join(phrases), st, cands, "resolved", round(conf, 3),
                                     covered=covered, lead=(True if lead else (False if st == "PARKED" else None)),
                                     lead_amb=(False if st == "PARKED" else None), tier_attr=(tier_attr if st == "WIDE" else None)))
        else:
            res.segments.append(_row(race_id, saddle_no, source_text_id, phase, " / ".join(phrases), None, cands, "ambiguous", None,
                                     covered=merged.get("covered") if isinstance(merged.get("covered"), bool) else None, lead=lead))
    # BREAK recovery: an explicit `remis/repris au trot` anywhere in the text marks the (single) break recovered;
    # the resumption phrase itself is not a second break.
    resumed = [e for e in res.events if re.search(r"(remise?|reprise?) au trot", e["source_phrase"])]
    others = [e for e in res.events if e not in resumed]
    if resumed and others:
        for e in others:
            if e["recovered"] is None:
                e["recovered"] = True
        res.events = others
    elif resumed:
        res.events = resumed[:1]
    for e in res.events:
        e.pop("_clause", None)
    return res
