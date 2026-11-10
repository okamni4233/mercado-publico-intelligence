"""Keyword matching shared by the scoring and the analysis-ready export.

Matching is done on whole words over accent-stripped lowercase text, so that
"obra" does not match "maniobra". Each entry maps a root to the pattern that
covers its accepted forms (singular and plural), so "obra" and "obras" count
as one keyword instead of two.
"""

from __future__ import annotations

import re
import unicodedata


KeywordPatterns = dict[str, re.Pattern[str]]


def _compile(patterns: dict[str, str]) -> KeywordPatterns:
    return {root: re.compile(rf"\b(?:{pattern})\b") for root, pattern in patterns.items()}


INDUSTRIAL_KEYWORDS = _compile(
    {
        "mantencion": r"mantencion(?:es)?",
        "industrial": r"industrial(?:es)?",
        "montaje": r"montajes?",
        "instrumentacion": r"instrumentacion",
        "electrico": r"electricos?",
        "reparacion": r"reparacion(?:es)?",
        "obra": r"obras?",
        "construccion": r"construccion(?:es)?",
        "campamento": r"campamentos?",
    }
)
CONSTRUCCION_KEYWORDS = {root: INDUSTRIAL_KEYWORDS[root] for root in ("obra", "construccion")}
SERVICIO_KEYWORDS = _compile(
    {
        "servicio": r"servicios?",
        "asesoria": r"asesorias?",
    }
)
EXCLUDED_KEYWORDS = _compile(
    {
        "catering": r"catering",
        "carpa": r"carpas?",
        "toldo": r"toldos?",
        "cubrepiso": r"cubrepisos?",
    }
)


def normalize_text(value: str) -> str:
    """Lowercase the text and strip accents."""

    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def count_keywords(text: str, keywords: KeywordPatterns) -> int:
    """Count the distinct keyword roots present in ``text`` as whole words.

    ``text`` must already be normalized with :func:`normalize_text`.
    """

    return sum(1 for pattern in keywords.values() if pattern.search(text))


def contains_any_keyword(text: str, keywords: KeywordPatterns) -> bool:
    """Tell whether at least one keyword root is present in ``text``."""

    return any(pattern.search(text) for pattern in keywords.values())
