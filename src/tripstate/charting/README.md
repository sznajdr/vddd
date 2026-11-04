# charting — BORIS export converter (RP-17)

Parses a BORIS aggregated-events export with the ethogram documented in `protocols/HAND-CHARTING/PROTOCOL.md` into `hand_charts` and `events` rows, computing fractions from the charter's T0/TEND point events and validating overlaps, uncharted gaps and required modifiers. CLI: `tools/boris_to_hand_charts.py`.
