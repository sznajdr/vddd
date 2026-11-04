"""Text normalisation for French notules: lowercase, accents stripped (NFD), apostrophes/quotes unified,
whitespace collapsed. Patterns in the lexicon are written against this normal form."""
from __future__ import annotations

import re
import unicodedata

_APOS = str.maketrans({"’": "'", "`": "'", "‘": "'", "«": '"', "»": '"', "“": '"', "”": '"', "œ": "oe", "Œ": "oe"})


def normalize(text: str) -> str:
    t = (text or "").translate(_APOS)
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t
