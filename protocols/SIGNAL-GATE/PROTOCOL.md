# SIGNAL-GATE — does trip information add edge over the market? (RP-7, KG-5)

**Purpose:** before spending ~100 owner-hours on video, test on existing **text** whether the trip states the pipeline will extract carry information the market does not already price. Uses the owner's Attelé notule corpus (2019-01-01 → 2026-05-23) and the §11 lexicon, which already exist. No video needed.

**This is a project go/no-go input, not a spec change.** The spec scopes prediction out; the owner's decision to continue is in scope.

## Design

1. **Features from prior races only** (§11.3 rule 6). For each runner in a target race, take its last k = 3 prior Attelé starts at Vincennes and derive, from `notule_runner_texte`, binary indicators per §11.2 family: `prior_parked` (« nez au vent », « sans dos » in outside context), `prior_covered` (« dans un dos », « à l'abri », « sillage »), `prior_leader`, `prior_wide` (« troisième épaisseur »…), `prior_break`. Count and most-recent versions.
2. **Market baseline:** closing odds (or the last available PMU odds snapshot) converted to normalized implied probability.
3. **Test:** logistic regression of `win` (and separately `placed`) on `logit(market_prob)` alone vs plus the trip indicators. Report log-loss and ROC AUC on a time-ordered holdout (last 12 months), and the coefficient signs. Also a simple stratified check: among runners with similar market probability bins, does `prior_parked = 1` shift the observed win rate?
4. **Guard:** the rolling-history leakage guard remains in force; no same-race text; no post-race fields.

## Decision rule (owner sets before running)

- Improvement in holdout log-loss ≥ a pre-registered minimum (suggest 0.002 nats/runner) **or** any trip indicator with a stable sign across yearly folds and |coef| > 2 × SE → **go**.
- Nothing survives → **stop or reframe**: either the market prices trip already, or the text is too coarse to tell. The second case argues for CV only if the first can be ruled out.

## Output

`data/signal_gate/report.md` with the tables; set KG-5 in `spec/registers/kill_gates.yaml`.

## Why this is cheap

Everything needed is a parser already drafted (`parsers_notule.py`), a corpus already assembled, and odds the owner already joins. One to two evenings.
