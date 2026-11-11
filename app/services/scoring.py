"""Rule-based scoring of detailed Mercado Publico licitations.

The score is a sum of fixed points for simple conditions (keywords in the text,
state, closing date, amount and region). Keywords, regions, points and
thresholds live in :class:`ScoringConfig`, so the same code can serve
different search profiles. The defaults are an example profile: industrial and
construction services for buyers in the north of Chile.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.services.keywords import (
    DEFAULT_EXCLUDED_WORDS,
    DEFAULT_INDUSTRIAL_WORDS,
    compile_keywords,
    contains_any_keyword,
    count_keywords,
    normalize_text,
)


PUBLISHED_STATE_CODE = 5
DEFAULT_PRIORITY_REGIONS = ["antofagasta", "tarapaca", "atacama"]
SCORE_COLUMNS = ["texto_busqueda", "contiene_keyword", "contiene_excluida", "score", "prioridad"]


class ScoringConfig(BaseModel):
    """Search profile and point values used by :func:`score_licitaciones`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_INDUSTRIAL_WORDS))
    excluded_keywords: list[str] = Field(default_factory=lambda: list(DEFAULT_EXCLUDED_WORDS))
    priority_regions: list[str] = Field(default_factory=lambda: list(DEFAULT_PRIORITY_REGIONS))
    amount_threshold: float = 10_000_000

    points_keyword: int = 30
    points_multiple_keywords: int = 20
    points_published: int = 15
    points_open: int = 15
    points_amount: int = 10
    points_region: int = 10
    penalty_excluded: int = 25

    high_priority_from: int = 70
    medium_priority_from: int = 40


def load_scoring_config(path: str | Path) -> ScoringConfig:
    """Load a scoring profile from a JSON file. Missing fields keep their default."""

    return ScoringConfig.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def score_licitaciones(
    df: pd.DataFrame,
    config: ScoringConfig | None = None,
    reference_date: datetime | str | None = None,
) -> pd.DataFrame:
    """Score detailed licitations and return a new DataFrame with the score columns.

    Expected input columns: nombre, descripcion, codigo_estado, fecha_cierre,
    monto_estimado and region_unidad. Missing columns simply add no points.

    ``reference_date`` is the date against which "still open" is decided. It
    defaults to the current moment, which makes the score change over time;
    pass a fixed date to get reproducible results.
    """

    active_config = config or ScoringConfig()

    if df.empty:
        output = df.copy()
        output["texto_busqueda"] = pd.Series(dtype="object")
        output["contiene_keyword"] = pd.Series(dtype="bool")
        output["contiene_excluida"] = pd.Series(dtype="bool")
        output["score"] = pd.Series(dtype="int64")
        output["prioridad"] = pd.Series(dtype="object")
        return output

    reference = pd.Timestamp(reference_date) if reference_date is not None else pd.Timestamp(datetime.now())
    keywords = compile_keywords(active_config.keywords)
    excluded = compile_keywords(active_config.excluded_keywords)
    regions = [normalize_text(region).strip() for region in active_config.priority_regions if region.strip()]

    output = df.copy()

    output["texto_busqueda"] = _build_texto_busqueda(output)
    normalized_text = output["texto_busqueda"].fillna("").map(normalize_text)
    keyword_count = normalized_text.map(lambda text: count_keywords(text, keywords))
    output["contiene_keyword"] = keyword_count.gt(0)
    output["contiene_excluida"] = normalized_text.map(lambda text: contains_any_keyword(text, excluded))

    empty = pd.Series(index=output.index, dtype="object")
    codigo_estado = pd.to_numeric(output.get("codigo_estado", empty), errors="coerce")
    fecha_cierre = pd.to_datetime(output.get("fecha_cierre", empty), errors="coerce")
    monto_estimado = pd.to_numeric(output.get("monto_estimado", empty), errors="coerce")
    region_normalized = output.get("region_unidad", empty).fillna("").astype(str).map(normalize_text)
    in_priority_region = region_normalized.map(lambda text: any(region in text for region in regions))

    score = pd.Series(0, index=output.index, dtype="int64")
    score = score + output["contiene_keyword"].astype(int) * active_config.points_keyword
    score = score + keyword_count.ge(2).astype(int) * active_config.points_multiple_keywords
    score = score + codigo_estado.eq(PUBLISHED_STATE_CODE).fillna(False).astype(int) * active_config.points_published
    score = score + fecha_cierre.gt(reference).fillna(False).astype(int) * active_config.points_open
    score = score + monto_estimado.gt(active_config.amount_threshold).fillna(False).astype(int) * active_config.points_amount
    score = score + in_priority_region.astype(int) * active_config.points_region
    score = score - output["contiene_excluida"].astype(int) * active_config.penalty_excluded

    output["score"] = score.clip(lower=0, upper=100).astype(int)
    output["prioridad"] = output["score"].map(lambda value: _score_to_priority(value, active_config))

    return output


def _build_texto_busqueda(df: pd.DataFrame) -> pd.Series:
    empty = pd.Series(index=df.index, dtype="object")
    nombre = df.get("nombre", empty).fillna("").astype(str)
    descripcion = df.get("descripcion", empty).fillna("").astype(str)
    return (nombre.str.strip() + " " + descripcion.str.strip()).str.strip()


def _score_to_priority(score: int, config: ScoringConfig) -> str:
    if score >= config.high_priority_from:
        return "alta"
    if score >= config.medium_priority_from:
        return "media"
    return "baja"
