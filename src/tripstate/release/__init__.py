"""Freeze → release tooling (SPEC-2.0.0-draft D-36, §7.2, §0.2).

`freeze`    — the D-36 freeze check as a library (registry, kill-gates, `[EG]` marker binding, `[OPEN]` markers).
`markers`   — binds every `[EG]` marker in the draft to registry entries / kill-gates; substitutes frozen values.
`instantiate` — OD-1x sheets + pilot reports → proposed registry instantiations (RECON §4 rules).
`promote`   — the promotion itself: frozen spec, frozen threshold set, decision log, version bump, changelog row.
`evaluate`  — DoD-1…6 release evaluation from the M8 store + golden manifest (B6).

None of this runs for real before OD-1x and the 5-race pilot (D-36). Every tool has a dry run on synthetic
fixtures so the mechanics are rehearsed before they matter.
"""
