"""Text-parse workstream (SPEC-2.0.0-draft §11; D-20). Post-race notule text -> hand_charts-shaped rows with
candidate sets, phases and evidence flags. The lexicon is the §11.2 / §11.4 table as data; `[C]` attestation
is re-measured on the owner's corpus by tools/lexicon_attest.py."""
from tripstate.textparse.lexicon import FAMILIES, PHASE_FAMILIES, STATE_DIMS, Family, candidates_for
from tripstate.textparse.normalize import normalize
from tripstate.textparse.parser import (
           MAPPING_RULE_VERSION,
           ParseResult,
           parse_notule,
           split_clauses,
)

__all__ = ["FAMILIES", "MAPPING_RULE_VERSION", "PHASE_FAMILIES", "STATE_DIMS", "Family", "ParseResult",
           "candidates_for", "normalize", "parse_notule", "split_clauses"]
