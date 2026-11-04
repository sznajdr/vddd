"""Seeding tool core (SPEC-2.0.0-draft §4 M3 tool DoD, §5.1; D-01, D-10, D-16; DR-03, DR-12).

`SeedingSession` is a pure state machine (no display, injectable clock) so the operator loop is
unit-testable; `tools/seed_cli.py` wraps it with an OpenCV window.
"""
from tripstate.seeding.session import KEYMAP, Candidate, Flag, Seed, SeedingSession

__all__ = ["KEYMAP", "Candidate", "Flag", "Seed", "SeedingSession"]
