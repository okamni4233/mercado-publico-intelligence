"""Keyword matching shared by the scoring and the analysis-ready export.

Matching is done on whole words over accent-stripped lowercase text, so that
"obra" does not match "maniobra". Keywords are written in singular; the plural
(-s, -es) is matched automatically, and a keyword and its plural count as one.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


KeywordPatterns = dict[str, re.Pattern[str]]

DEFAULT_INDUSTRIAL_WORDS = [
    "mantencion",
    "industrial",
    "montaje",
    "instrumentacion",
    "electrico",
    "reparacion",
    "obra",
    "construccion",
    "campamento",
]
DEFAULT_EXCLUDED_WORDS = ["catering", "carpa", "toldo", "cubrepiso"]


def normalize_text(value: str) -> str:
    """Lowercase the text and strip accents."""

    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def compile_keywords(words: Iterable[str]) -> KeywordPatterns:
    """Build one whole-word pattern per keyword root.

    Words are normalized, blanks are dropped and a word that is just the plural
    of another one in the list ("obras" next to "obra") is merged into it, so
    the same root is never counted twice.
    """

    cleaned = [normalize_text(word).strip() for word in words]
    unique = list(dict.fromkeys(word for word in cleaned if word))
    plurals = {root + suffix for root in unique for suffix in ("s", "es")}
    roots = [word for word in unique if word not in plurals]
    return {root: re.compile(rf"\b{re.escape(root)}(?:s|es)?\b") for root in roots}


INDUSTRIAL_KEYWORDS = compile_keywords(DEFAULT_INDUSTRIAL_WORDS)
CONSTRUCCION_KEYWORDS = compile_keywords(["obra", "construccion"])
SERVICIO_KEYWORDS = compile_keywords(["servicio", "asesoria"])
EXCLUDED_KEYWORDS = compile_keywords(DEFAULT_EXCLUDED_WORDS)


def count_keywords(text: str, keywords: KeywordPatterns) -> int:
    """Count the distinct keyword roots present in ``text`` as whole words.

    ``text`` must already be normalized with :func:`normalize_text`.
    """

    return sum(1 for pattern in keywords.values() if pattern.search(text))


def contains_any_keyword(text: str, keywords: KeywordPatterns) -> bool:
    """Tell whether at least one keyword root is present in ``text``."""

    return any(pattern.search(text) for pattern in keywords.values())
