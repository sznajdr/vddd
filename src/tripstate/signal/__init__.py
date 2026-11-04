"""Signal gate (protocols/SIGNAL-GATE; RP-7; KG-5): do prior-race trip phrases carry information beyond the
closing market? Prior races only (§11.3 rule 6), time-ordered evaluation, pre-registered decision rule."""
from tripstate.signal.corpus import RunnerRow, load_corpus_csv, synthetic_corpus
from tripstate.signal.features import INDICATORS, build_features
from tripstate.signal.gate import run_gate
from tripstate.signal.model import LogisticRegression, auc, log_loss

__all__ = ["INDICATORS", "LogisticRegression", "RunnerRow", "auc", "build_features", "load_corpus_csv", "log_loss", "run_gate", "synthetic_corpus"]
