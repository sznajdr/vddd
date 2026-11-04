"""§11.2 vocabulary as data (SPEC-2.0.0-draft; D-20) plus the §11.4 phase table (DR-08).

Each Family asserts PARTIAL trip dimensions; a §2.3 state is emitted only when it is the single state
consistent with everything asserted in the clause (§11.3 rule 1 and 3). Dimensions:
  tier    1 = rail line, 2 = outside (deuxième épaisseur), 3 = three-wide or more
  covered True / False
  depth   runners ahead in the rail/outside chain: 0 = leader, 1 = exactly one, 2 = two or more ('na' for WIDE)
`evidence` copies the spec's flags: C = attested in the owner's corpus per §11.1, P = encoded in parsers_notule.py.
Re-measure attestation with tools/lexicon_attest.py before activating text parsing (§11.4 rule).
Patterns match the normalised text (see normalize.py): no accents, lowercase, straight apostrophes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_ANIM = r"(?:l'anim(?:ateur|atrice)|du leader|de l'animateur|de l'animatrice)"


@dataclass(frozen=True)
class Family:
    id: str
    target: str                     # state name, 'OVERLAY:DETACHED', 'EVENT:BREAK', 'RESERVED:STRETCH_BLOCK', 'EXCLUDED', 'PROXIMITY'
    pattern: str                    # regex on normalised text
    asserts: dict = field(default_factory=dict)   # dimension -> value or frozenset of values
    evidence: str = "C"
    note: str = ""
    lead: bool | None = None        # PARKED families that also assert lead_uncovered_outside
    tier_attr: int | None = None
    end_attr: str | None = None
    recovered: bool | None = None

    @property
    def regex(self) -> re.Pattern:
        return re.compile(self.pattern)


S = frozenset
STATE_DIMS: dict[str, dict] = {
    "LEADER": {"tier": 1, "covered": False, "depth": 0},
    "POCKET": {"tier": 1, "covered": True, "depth": 1},
    "RAIL_COVERED": {"tier": 1, "covered": True, "depth": 2},
    "RAIL_UNCOVERED": {"tier": 1, "covered": False, "depth": S({1, 2})},
    "OUTSIDE_COVERED": {"tier": 2, "covered": True},
    "PARKED": {"tier": 2, "covered": False},
    "WIDE": {"tier": 3, "depth": S({"na"})},   # covered either; no rail-chain position, so any depth assertion excludes it
}

FAMILIES: list[Family] = [
    # ---- exclusions / proximity first (checked before direct families)
    Family("leader_proximity", "PROXIMITY", r"\b(groupe de tete|tete du wagon|les animateurs|des animateurs)\b", note="proximity, not sole leadership (§11.2 LEADER note)"),
    Family("finish_quality_excluded", "EXCLUDED", r"\b(rapidement faibli|completement cede|largement domine|a faibli|a cede)\b", note="rule 7: not a trip mapping, never DETACHED"),
    Family("relegation_excluded", "EXCLUDED", r"\b(retrograde|declasse)e?s?\b.*\b(enquete|jury|commissaires)\b|\b(enquete|jury|commissaires)\b.*\b(retrograde|declasse)", note="rule 7: relegation is never BREAK; evidence for arrival_revision_type only"),
    Family("largement_excluded", "EXCLUDED", r"\blargement\b(?! domine)", note="« largement » is unrelated to WIDE"),
    # ---- LEADER
    Family("leader_en_tete", "LEADER", r"\b(en tete|au commandement|aux commandes)\b", {"tier": 1, "covered": False, "depth": 0}, "C"),
    Family("leader_pris_la_tete", "LEADER", r"\b(pris|prendre|prend|a pris|prenant) la tete\b", {"tier": 1, "covered": False, "depth": 0}, "C"),
    Family("leader_installe_en_tete", "LEADER", r"\b(venue?|installee?|rabattue?) en tete\b", {"tier": 1, "covered": False, "depth": 0}, "C"),
    # ---- POCKET-ish: cover behind the leader, rail not proven -> {POCKET, OUTSIDE_COVERED}
    Family("pocket_dos_animateur", "POCKET", rf"\bdans le dos (?:de )?{_ANIM}\b|\bdos du leader\b", {"covered": True, "depth": 1}, "C", "cover behind the leader; rail placement unproven"),
    Family("pocket_sillage_animateur", "POCKET", rf"\bdans le sillage (?:de )?{_ANIM}\b", {"covered": True, "depth": 1}, "C"),
    # ---- rail lines
    Family("rail_line_numbered", "RAIL_COVERED", r"\b(deuxieme|seconde) ligne a la corde\b", {"tier": 1, "covered": True, "depth": 1}, "C", "second rail line = POCKET"),
    Family("rail_line_deep", "RAIL_COVERED", r"\b(troisieme|quatrieme|cinquieme) ligne a la corde\b", {"tier": 1, "covered": True, "depth": 2}, "C"),
    Family("rail_covered_generic", "RAIL_COVERED", r"\b(ligne|rang) cote corde\b|\bpeloton cote corde\b|\ble long de la corde\b", {"tier": 1, "covered": True}, "C", "depth unresolved -> {POCKET, RAIL_COVERED}"),
    Family("rail_bare", "RAIL_UNCOVERED", r"\b(a la corde|cote corde)\b", {"tier": 1}, "C", "bare rail placement: no cover information"),
    Family("sans_dos", "RAIL_UNCOVERED", r"\bsans dos\b", {"covered": False, "depth": S({1, 2})}, "C", "uncovered non-leader; bare -> {RAIL_UNCOVERED, PARKED, WIDE}"),
    # ---- cover (outside or rail unresolved)
    Family("cover_dans_un_dos", "OUTSIDE_COVERED", r"\bdans un dos\b|\bun bon dos\b|\btrouve le dos\b", {"covered": True}, "C"),
    Family("cover_sillage", "OUTSIDE_COVERED", r"\b(dans|prendre|pris|profiter|profite) (?:le |du |d'un )?sillage\b", {"covered": True}, "C"),
    Family("cover_abri", "OUTSIDE_COVERED", r"\ba l'abri\b|\b(progresse|rapprochee?) a l'abri\b", {"covered": True}, "C"),
    Family("cover_ramene_par", "OUTSIDE_COVERED", r"\bramenee? par\b", {"covered": True}, "C"),
    Family("outside_wagon_exterieur", "OUTSIDE_COVERED", r"\bwagon de l'exterieur\b", {"tier": 2, "covered": True}, "C"),
    Family("outside_en_dehors", "OUTSIDE_COVERED", r"\ben dehors\b(?! de l'anim)|\ben deuxieme epaisseur\b|\ben seconde epaisseur\b", {"tier": 2}, "C", "outside tier; cover unresolved -> {OUTSIDE_COVERED, PARKED}"),
    # ---- PARKED
    Family("parked_nez_au_vent", "PARKED", r"\bnez au vent\b", {"covered": False}, "C", "no cover; tier unresolved unless outside context"),
    Family("parked_hauteur_animateur", "PARKED", rf"\b(a hauteur|aux cotes|a cote|au dehors|en dehors) (?:de )?{_ANIM}\b|\bcote de l'animateur\b|\bdehors de l'animateur\b", {"tier": 2, "covered": False}, "C", "alongside the leader", lead=True),
    # ---- WIDE
    Family("wide_troisieme", "WIDE", r"\ben troisieme epaisseur\b", {"tier": 3}, "C", tier_attr=3),
    Family("wide_quatrieme", "WIDE", r"\ben quatrieme epaisseur\b", {"tier": 3}, "C", tier_attr=4),
    Family("wide_tout_en_dehors", "WIDE", r"\btout en dehors\b|\bau large\b", {"tier": 3}, "C"),
    # ---- DETACHED overlay
    Family("detached_front_or_rear", "OVERLAY:DETACHED", r"\b(s'est )?detachee?\b", {}, "C", "end needs context (front with LEADER evidence)"),
    Family("detached_rear", "OVERLAY:DETACHED", r"\b(en (?:tres )?net retrait|loin du groupe|dans le lointain|attardee?|decrochee?)\b", {}, "C", end_attr="rear"),
    Family("rank_only_not_detached", "EXCLUDED", r"\ben queue de peloton\b|\ben retrait\b(?! net)", note="rank, not a gap above detach_sl"),
    # ---- BREAK events
    Family("break_enleve", "EVENT:BREAK", r"\bs'est enlevee?\b|\bs'enlevant\b", {}, "P"),
    Family("break_faute", "EVENT:BREAK", r"\b(a fait|commis|fait|sur) une faute\b|\bfaute (au depart|au tournant|dans le (?:dernier )?tournant|a l'entree de la ligne droite|dans la ligne droite)\b|\bapres sa faute\b|\bperdu du terrain sur une faute\b", {}, "P"),
    Family("break_remis_au_trot", "EVENT:BREAK", r"\b(remise?|reprise?) au trot\b", {}, "P", recovered=True),
    Family("dai_mention", "EXCLUDED", r"\bdisqualifiee?\b|\bdai\b", note="official outcome; not proof of a break unless the text also states one"),
    # ---- STRETCH_BLOCK (reserved v1.5)
    Family("stretch_block_reserved", "RESERVED:STRETCH_BLOCK", r"\b(bloquee?|enfermee?|genee?|n'a (?:jamais )?pu s'exprimer|a tarde a pouvoir s'exprimer|n'a pu se degager|(chercher|cherche|trouver|trouve) l'ouverture|(voir|vu|trouver|trouve) le jour|n'a pas eu le passage)\b", {}, "C"),
]

PHASE_FAMILIES: list[tuple[str, str, str]] = [   # (pattern, phase, evidence)
    (r"\bdes le depart\b|\bau depart\b|\bdans les premiers metres\b", "early", "C"),
    (r"\ba mi-?parcours\b|\ba mi-?course\b", "mid", "C"),
    (r"\bdans le dernier tournant\b|\ba l'entree de la ligne droite\b|\bdans la montee\b", "late", "C"),
    (r"\bdans la ligne droite\b|\bsur le poteau\b|\bau poteau\b", "stretch", "C"),
    (r"\ben fin de course\b|\bsur la fin\b", "late", "C"),
]


def _consistent(state_dims: dict, asserted: dict) -> bool:
    for dim, val in asserted.items():
        if dim not in state_dims:
            continue  # the state does not constrain this dimension (e.g. WIDE / covered)
        sv = state_dims[dim]
        svs = sv if isinstance(sv, frozenset) else S({sv})
        avs = val if isinstance(val, frozenset) else S({val})
        if not (svs & avs):
            return False
    return True


def candidates_for(asserted: dict) -> list[str]:
    """All §2.3 geometric states consistent with the asserted dimensions (sorted)."""
    return sorted(s for s, dims in STATE_DIMS.items() if _consistent(dims, asserted))


def merge_assertions(parts: list[dict]) -> dict | None:
    """Intersect dimension assertions from several families; None when contradictory."""
    out: dict = {}
    for a in parts:
        for dim, val in a.items():
            vs = val if isinstance(val, frozenset) else S({val})
            if dim in out:
                inter = out[dim] & vs
                if not inter:
                    return None
                out[dim] = inter
            else:
                out[dim] = vs
    return {d: (next(iter(v)) if len(v) == 1 else v) for d, v in out.items()}
