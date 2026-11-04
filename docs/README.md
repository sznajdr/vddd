# docs/ — index

**Live documents** (kept current; `make lint-docs` checks that the paths they name exist):

| File | What |
|---|---|
| `HANDOFF-NEXT-SESSION.md` | start here in a fresh session: reading order, green checks, the next executable queue, owner-side items, phases |
| `ARCHITECTURE.md` | module graph with implementation status, the two stacks, data flow for one race, determinism boundary, the freeze → calibration → release chain |
| `BACKLOG.md` | prioritized remaining work with effort and what it unlocks; ✅ = done with the date |
| `AUDIT.md` | every coherence check that found something, what was wrong, what changed; open items |
| `RISK-REGISTER.md` | ranked risks with the cheapest falsifier each |
| `GLOSSARY.md` | trot vocabulary and project terms |
| `STACK-2.0.md` | accepted (non-normative, D-15) default stack for pilot and production |
| `decisions/` | owner decision memos; `2026-11-04-continuation.md` settles the delegated design queue (applied as ledger L-46…L-50) |
| `agent-prompts/` | build prompts per module; each carries a status line saying what is already done |

**Reference material** (historical or external; not re-validated on every change):

| Folder | What |
|---|---|
| `research/` | the 2026-11-04 research pack: 11 notes mapped to modules and decisions, `SOURCES.md` for every URL; numbers quoted from search summaries are marked unverified |

Repository-level documents outside this folder: `README.md` (map), `STATUS.md` (live board), `ROADMAP.md` (phases and exit gates), `CLAUDE.md` (rules for agents), `spec/README.md`, `tools/README.md`, `protocols/README.md`, `src/tripstate/README.md`, `data/README.md`.
