# 09 — Domain literature: trip effects, existing chart notations, text vs video

## Question
Is there evidence that the states this project extracts (cover, parked, first-over, breaks) matter physically and predictively, and do existing charting conventions already encode them?

## Findings

- **Drafting is physically real for horses.** Spence, Thurman, Maher & Wilson, *Biology Letters* 8(4):678–681 (2012), used TurfTrax radio tracking from UK Thoroughbred seasons 2005–2007 (reported 44,803 runners, 3,357 races) and found that horses spending more of the race directly behind another horse went significantly faster; pacing strategy varied with distance. ([PMC3391435](https://pmc.ncbi.nlm.nih.gov/articles/PMC3391435), [RVC record](https://rvc-repository.worktribe.com/output/1416321))
- **Harness-specific glossaries** define *parked* (racing outside with ≥ 1 horse between you and the rail, losing ground on every turn), *cover* (wind shelter behind another horse), *first-over* (first horse to move on the leader on the outside), and the *pocket* (shortest trip + shelter, but boxed). ([Standardbred Canada glossary](https://standardbredcanada.ca/content/standardbred-harness-racing-glossary.html), [USTA fan guide](https://fanguide.ustrotting.com/racetrack-experience.cfm))
- **Existing chart notations already encode trip.** Illinois racing rules require standard symbols for *breaks* and *parked out* on performance lines; TrackMaster's HarnessPro computes a "parked propensity" from the last 10 starts at each quarter call and a pace-style position at each of four calls; trip notes like "parked", "3-wide last quarter" are routine in US charts. ([Illinois Admin Code](https://my.ilga.gov/ftp/JCAR/AdminCode/011/011004150000400R.html), [TrackMaster help](http://info.trackmaster.com/harness/prohelp.htm), [TrackMaster PP launch](https://ustrottingnews.com/?p=66820)) *The exact superscript convention could not be confirmed from a primary key; check a track program legend.*
- **Academic predictive work using positions** exists for harness racing (quarter and stretch positions as inputs to support-vector regression of finish position, Schumaker). ([paper](https://www.robschumaker.com/publications/DSS%20-%20Machine%20Learning%20the%20Harness%20Track%20-%20Crowdsourcing%20and%20Varying%20Race%20History.pdf))
- **No regression study of parked/first-over effects on win probability** was found in searchable literature; no Swedish/French trot study of race tactics by position was found.
- **Text can rival video for event spotting:** "Do We Need Large VLMs for Spotting Soccer Actions?" (IJCNLP-AACL 2025 SRW) uses timestamped commentary with LLM judges and claims comparable event detection to video-based spotters, training-free. ([arXiv 2506.17144](https://arxiv.org/html/2506.17144v2))

## Implications for the spec

1. **The taxonomy is grounded.** Cover (drafting) has a measured speed effect in horses; parked/first-over/pocket are the long-standing handicapping variables; US charts prove the states are chartable by humans at scale. Nothing found argues for adding or removing a v1 state.
2. **The money-state choice (D-27, uncovered-outside mask) matches the physics** better than the label: what costs energy is being outside *and* uncovered, independent of which lane.
3. **Signal gate (RP-7) is the right first test**, and the soccer commentary result is a warning in both directions: the notule text may already carry most of the trip signal (then CV adds resolution, not information), or it may not (then CV is the only source). Either answer is useful before charting.
4. **A convention to borrow:** report per-runner trip at fixed race-fraction *calls* (e.g. 0.25 / 0.50 / 0.75 / stretch) in the feature export, alongside the segment payload. This is a downstream view, not a schema change, and it makes the output comparable to the US chart tradition.
