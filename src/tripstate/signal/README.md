# signal — the signal gate (RP-7, KG-5)

Prior-race trip indicators (parsed with `textparse`, strictly earlier dates only) added to a market-logit baseline in a numpy
logistic regression (IRLS, ridge); time-ordered 12-month holdout, race-level bootstrap CI on the log-loss gain, rolling folds
for coefficient sign stability; pre-registered rule in `protocols/SIGNAL-GATE/decision.yaml`. `synthetic_corpus(trip_effect)`
generates a controllable corpus with lexicon-based notules so the whole chain is testable: injected effect → GO, none → NO-GO.
