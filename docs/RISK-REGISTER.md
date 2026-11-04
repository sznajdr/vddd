# Risk register

Ranked by (likelihood × damage). "Test" names the cheapest falsifier. Status as of 2026-11-04.

| # | Risk | If true | Test | Status |
|---|---|---|---|---|
| R-1 | **Trip states add no edge over the market** | project has no value even if it works | `protocols/SIGNAL-GATE` on existing text + odds (1–2 evenings) | untested |
| R-2 | **Seeding 14 saddle numbers at broadcast resolution takes > 8 min** (D-01 human premise) | human-in-the-loop design fails; KG-1 | OD-1x step 1 (one afternoon) | untested |
| R-3 | **Official LeTrot tracking data already exists** | large parts of M2–M4 redundant; or a far better source | read the two LeTrot "Tracking" pages (30 min) | untested (RP-6) |
| R-4 | **Lateral scale is wrong**: SW = SL × 0.35 ignores camera yaw; lanes may be ≈ 0.34 SW apart at 20° yaw | `same_tier_sw = 0.6` merges lanes; a parked horse reads as covered; headline metric meaningless | OD-1x step 4 ratios at three track locations | untested (RP-5) |
| R-5 | **Bends** put ≈ 1 SW of false lateral spread on a 40 m pack with a straight axis | tier flicker on every turn | OD-1x step 4 bend frame | untested |
| R-6 | **Replay rights / availability** | no corpus | read Equidia terms; confirm replays downloadable at usable resolution | unchecked |
| R-7 | **Anchor bias ≥ tolerance on volte starts** | silent corpus loss via EC-12 → Q-3 | OD-1x step 2 | untested (D-34) |
| R-8 | **Yield after 7 conjunctive gates ≈ 50 %, MNAR by stratum** | biased corpus | pilot per-stratum yield (D-35) | untested |
| R-9 | **Wide-pan coverage below Q-1/Q-2 on real broadcasts** | most races unchartable | OD-1x step 3 | untested |
| R-10 | **Finish shots show < 3 identifiable crossings** | D-30 makes `official_assumed` unreachable; EC-12 inconclusive everywhere | OD-1x step 5 | untested |
| R-11 | **GPU nondeterminism breaks DoD-5** | re-runs differ | mitigated by D-32 quantization; verify on pilot | mitigated |
| R-12 | **Selection bias from ≤ 14 cap and big-race realizations** | corpus misses the deepest pools | acknowledged (DR-11), `qc.realization` quantifies | accepted |
| R-13 | **D-26 table gap** (tier-1 leader covered by outside runner) | undefined state | reference impl emits UNKNOWN + reason; owner decides | open (RP-11) |
| R-14 | **Owner time**: ~100 h to a 600-race corpus at 5 min/race + charting | project stalls | DoD-3 pilot distribution; DR-12 2× playback | untested |
| R-15 | **SAM-based seeded tracking too slow at 14 objects** (SAM 3 near real-time at ~5 objects; SAM 2 memory scales with objects) | seeding design falls back to detector+tracker with post-hoc assignment | pilot timing on one OD-1x replay with 14 prompts | untested (research 02) |
| R-16 | **No public horse-racing detection/tracking data exists**; the only academic set is 15 private videos | every label is owner time; no shortcut | confirmed by search | accepted (research 01) |
| R-17 | **Licence constraints** (Ultralytics AGPL-3.0; Meta SAM terms) for any future distribution | stack substitution | read licences before production | open (STACK-2.0) |
| R-18 | **Lateral tiering may be impossible on most of the lap from the main camera** (elevation of a few degrees on far sections compresses lateral metres to ~5 % of longitudinal) | the corpus can tier only in front of the stands; Q-1/Q-2 pass while tiers are `UNKNOWN` elsewhere | OD-1x step 4 per-section view angle + fence–rail separation; simulator prediction in research 11 | predicted (RP-24) |
