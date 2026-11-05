# protocols/ — what a human does, in order

Human protocols are followed by the owner with a stopwatch and a notebook (CLAUDE.md rule 8); tools only make recording easier. Each folder is one owner-side activity, and each says which register or gate it feeds.

| Folder | When | Produces | Feeds |
|---|---|---|---|
| `OD-1x/` | P2, one afternoon, three replays (autostart, flat volte, handicap volte) | the six sheets in `data/od1x/` | every `[EG]` value via `tools/instantiate_eg.py`; KG-1, KG-4 |
| `SIGNAL-GATE/` | P3, one evening, the owner's notule + odds corpus | a go/no-go per `decision.yaml` via `tools/signal_gate.py` | KG-5 (project go/no-go before P4) |
| `PILOT-5/` | P4, five races on the throwaway stack | `data/pilot5/pilot_report.md`, filled `kill_gates.yaml` | KG-2, KG-3, D-29 budget keys (`instantiate_eg.py --pilot-reports`) |
| `HAND-CHARTING/` | P6 only, after the freeze (D-36) | `hand_charts` rows via BORIS + `tools/boris_to_hand_charts.py` | golden set, calibration (§7), DoD-1/2/6 |
| `OPERATOR/` | before P2 and at every seeding session | keymap card, ten-minute walkthrough, anchor prompts per start type | fewer protocol errors; real human-minutes |

Rehearse before the real day: `make od1x-rehearsal` (synthetic clip, sheet templates, scripted stopwatch, instantiation proposals), `make pilot-demo` (the whole pilot loop on synthetic video), `make freeze-dry-run` (sheets → registry → simulated promotion).
