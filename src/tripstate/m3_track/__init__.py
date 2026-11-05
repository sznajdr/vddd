"""M3 — Tracking + seeding (SPEC-2.0.0-draft §4 M3; D-01, D-23…D-25, D-30).

`checks`: finish/start/anchor consistency checks (non-corrective). `assignments`: `id_assignments` rows from operator
seeds with RP-18 click provenance (L-51). The live seeding loop is `tripstate.seeding`; the throwaway comparison
path is `tripstate.pilot`.
"""
from tripstate.m3_track.assignments import (
    box_ref,
    id_assignment_rows,
    rows_from_pilot,
    rows_from_session,
)

__all__ = ["box_ref", "id_assignment_rows", "rows_from_pilot", "rows_from_session"]
