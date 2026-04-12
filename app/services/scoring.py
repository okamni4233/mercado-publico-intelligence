"""Scoring helpers for detailed Mercado Publico licitations."""

from __future__ import annotations

import unicodedata
from datetime import datetime

import pandas as pd


INDUSTRIAL_KEYWORDS = [
    "mantencion",
    "industrial",
    "montaje",
    "instrumentacion",
    "electrico",
    "reparacion",
    "obra",
    "obras",
    "construccion",
    "campamento",
    "campamentos",
]

EXCLUDED_KEYWORDS = ["catering", "carpa", "toldos", "cubrepiso"]
PRIORITY_REGIONS = ["antofagasta", "tarapaca", "atacama"]


def score_licitaciones(df: pd.DataFrame) -> pd.DataFrame:
    """Score detailed licitations and return a new analysis-ready DataFrame.

    Expected input columns include at least:
    - nombre
    - descripcion
    - codigo_estado
    - fecha_cierre
    - monto_estimado
    - region_unidad
    """

    if df.empty:
        output = df.copy()
        output["texto_busqueda"] = pd.Series(dtype="object")
        output["contiene_keyword"] = pd.Series(dtype="bool")
        output["contiene_excluida"] = pd.Series(dtype="bool")
        output["score"] = pd.Series(dtype="int64")
        output["prioridad"] = pd.Series(dtype="object")
        return output

    output = df.copy()

    output["texto_busqueda"] = _build_texto_busqueda(output)
    normalized_text = output["texto_busqueda"].fillna("").map(_normalize_text)
    keyword_count = normalized_text.map(_count_industrial_keywords)
    output["contiene_keyword"] = keyword_count.gt(0)
    output["contiene_excluida"] = normalized_text.map(_contains_excluded_keywords)

    codigo_estado = pd.to_numeric(output.get("codigo_estado"), errors="coerce")
    fecha_cierre = pd.to_datetime(output.get("fecha_cierre"), errors="coerce")
    monto_estimado = pd.to_numeric(output.get("monto_estimado"), errors="coerce")
    region_normalized = output.get("region_unidad", pd.Series(index=output.index, dtype="object")).fillna("").map(_normalize_text)

    score = pd.Series(0, index=output.index, dtype="int64")
    score = score + output["contiene_keyword"].astype(int) * 30
    score = score + keyword_count.ge(2).astype(int) * 20
    score = score + codigo_estado.eq(5).fillna(False).astype(int) * 15
    score = score + fecha_cierre.gt(pd.Timestamp(datetime.now())).fillna(False).astype(int) * 15
    score = score + monto_estimado.gt(10_000_000).fillna(False).astype(int) * 10
    score = score + region_normalized.map(_is_priority_region).astype(int) * 10
    score = score - output["contiene_excluida"].astype(int) * 25

    output["score"] = score.clip(lower=0, upper=100).astype(int)
    output["prioridad"] = output["score"].map(_score_to_priority)

    return output


def score_oportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible wrapper for the previous placeholder name."""

    return score_licitaciones(df)


def _build_texto_busqueda(df: pd.DataFrame) -> pd.Series:
    nombre = df.get("nombre", pd.Series(index=df.index, dtype="object")).fillna("").astype(str)
    descripcion = df.get("descripcion", pd.Series(index=df.index, dtype="object")).fillna("").astype(str)
    return (nombre.str.strip() + " " + descripcion.str.strip()).str.strip()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _count_industrial_keywords(text: str) -> int:
    normalized_keywords = {_normalize_text(keyword) for keyword in INDUSTRIAL_KEYWORDS}
    return sum(1 for keyword in normalized_keywords if keyword in text)


def _contains_excluded_keywords(text: str) -> bool:
    normalized_keywords = {_normalize_text(keyword) for keyword in EXCLUDED_KEYWORDS}
    return any(keyword in text for keyword in normalized_keywords)


def _is_priority_region(text: str) -> bool:
    return any(region in text for region in PRIORITY_REGIONS)


def _score_to_priority(score: int) -> str:
    if score >= 70:
        return "alta"
    if score >= 40:
        return "media"
    return "baja"
