# textparse — §11 lexicon bridge (text_parse filler)

`lexicon.py` holds the §11.2 families as data: each asserts partial trip dimensions (tier, covered, depth); `candidates_for`
returns the §2.3 states consistent with a clause's assertions and a state is emitted only when exactly one remains
(rules 1 and 3). Phases come from the §11.4 table (rule 4); fractions are never fabricated. Negated, quoted and other-subject
hits are recorded but not asserted (rule 2). Break families create pending `BREAK` events (rule 8); relegation and finish-quality
families are excluded (rule 7); `STRETCH_BLOCK` families are recorded as reserved. Confidence = semantic specificity × phase
certainty, never PMI (rule 5). `[C]`/`[P]` flags are copied from the spec; `tools/lexicon_attest.py` re-measures them.
Output rows are `hand_charts`-shaped with the schema-additive columns. `tools/parse_notules.py` batch-parses a corpus.
