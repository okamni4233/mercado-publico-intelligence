from __future__ import annotations

import pandas as pd
import pytest

from app.services.keywords import (
    EXCLUDED_KEYWORDS,
    INDUSTRIAL_KEYWORDS,
    contains_any_keyword,
    count_keywords,
    normalize_text,
)
from app.services.scoring import score_licitaciones


def _licitacion(nombre: str, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "nombre": nombre,
        "descripcion": "",
        "codigo_estado": None,
        "fecha_cierre": None,
        "monto_estimado": None,
        "region_unidad": "",
    }
    base.update(overrides)
    return base


def _score(nombre: str, **overrides: object) -> pd.Series:
    return score_licitaciones(pd.DataFrame([_licitacion(nombre, **overrides)])).iloc[0]


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Obras menores", 1),
        ("Obra y obras de mejoramiento", 1),
        ("Servicio de maniobra de grúa", 0),
        ("Mano de obra para mantención eléctrica", 2),
        ("Mantenciones y reparaciones de campamentos", 3),
        ("Compra de sobras industrializadas", 0),
        ("Adquisición de insumos de oficina", 0),
    ],
)
def test_count_keywords_uses_whole_words_and_counts_each_root_once(texto: str, esperado: int) -> None:
    assert count_keywords(normalize_text(texto), INDUSTRIAL_KEYWORDS) == esperado


def test_excluded_keywords_match_whole_words_only() -> None:
    assert contains_any_keyword(normalize_text("Arriendo de carpas y toldos"), EXCLUDED_KEYWORDS)
    assert not contains_any_keyword(normalize_text("Reparación de escarpado"), EXCLUDED_KEYWORDS)


def test_obras_menores_scores_a_single_keyword() -> None:
    row = _score("Obras menores")

    assert bool(row["contiene_keyword"]) is True
    assert row["score"] == 30
    assert row["prioridad"] == "baja"


def test_maniobra_is_not_an_industrial_keyword() -> None:
    row = _score("Servicio de maniobra de grúa")

    assert bool(row["contiene_keyword"]) is False
    assert row["score"] == 0
    assert row["prioridad"] == "baja"


def test_two_different_keywords_get_the_multiple_keyword_bonus() -> None:
    row = _score("Mantención de obras")

    assert row["score"] == 50
    assert row["prioridad"] == "media"


def test_all_positive_rules_add_up_to_the_maximum() -> None:
    row = _score(
        "Mantención industrial",
        codigo_estado=5,
        fecha_cierre="2200-01-01T00:00:00",
        monto_estimado=20_000_000,
        region_unidad="Región de Antofagasta",
    )

    assert row["score"] == 100
    assert row["prioridad"] == "alta"


def test_excluded_keyword_subtracts_and_score_never_goes_below_zero() -> None:
    con_keyword = _score("Montaje de carpas")
    sin_keyword = _score("Servicio de catering")

    assert bool(con_keyword["contiene_excluida"]) is True
    assert con_keyword["score"] == 5
    assert sin_keyword["score"] == 0


def test_past_closing_date_and_small_amount_add_nothing() -> None:
    row = _score("Construcción de sede", fecha_cierre="2000-01-01T00:00:00", monto_estimado=5_000_000)

    assert row["score"] == 30


def test_empty_dataframe_returns_scoring_columns() -> None:
    result = score_licitaciones(pd.DataFrame())

    assert result.empty
    for column in ("texto_busqueda", "contiene_keyword", "contiene_excluida", "score", "prioridad"):
        assert column in result.columns
