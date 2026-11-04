# Glossary

| Term | Meaning |
|---|---|
| **Attelé** | Harness trot (driver in a sulky). Monté (ridden trot) is excluded. |
| **Autostart** | Mobile-gate start; runners line up behind a car. `t_0` = gate-car pull-away. |
| **Volte** | Standing start where runners turn into the racing direction; `t_0` = final release. Flat (all same distance) or handicap (rendements). |
| **Rendement** | Distance handicap in metres (multiples of 25) that a runner concedes; `distance_run_m = base + rendement`. |
| **RK / réduction kilométrique** | Time per kilometre, the headline "time" in French trot. A rate, not a duration (D-24). |
| **Piste** | Track configuration at Vincennes: GP (grande piste) or PP (petite piste). From ingest, never inferred. |
| **Corde** | The inside rail. Tier 1 = on the rail. |
| **SL / SW** | Sulky length / sulky width: pack-relative units (D-07). SW = SL × `sw_ratio` (RP-5: suspect). |
| **Tier** | Lateral lane index from the rail outward, from deterministic clustering of `w_sw`. |
| **Cover** | Being directly behind another runner within `[cover_min_sl, cover_max_sl]` and within `cover_lat_sw` laterally (D-26, tier-independent). |
| **PARKED** | Tier 2, uncovered: the "money state" (nez au vent). |
| **lead_uncovered_outside** | The uniquely furthest-advanced PARKED runner in a frame (was `first_over`; positional sense). |
| **DAI** | Disqualifié pour allures irrégulières: disqualified for breaking gait. |
| **Notule** | Post-race per-runner text comment (`notule_runner_texte`), the owner's NLP corpus. |
| **EG** | Evidence-gated: a provisional number that blocks the freeze until measured. |
| **Kill-gate (KG)** | Abort criterion for the project (§0.4). |
| **OD-1x** | The one-afternoon timed dry run on three replays that instantiates every EG value. |
| **Golden set** | 40 hand-charted races (30 dev / 10 held-out), charted only after the freeze. |
