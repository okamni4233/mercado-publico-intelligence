from __future__ import annotations

import pandas as pd
import pytest

from app.services.keywords import (
    EXCLUDED_KEYWORDS,
    INDUSTRIAL_KEYWORDS,
    compile_keywords,
    contains_any_keyword,
    count_keywords,
    normalize_text,
)
from app.services.scoring import ScoringConfig, load_scoring_config, score_licitaciones


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
    for column in ("texto_busqueda", "contiene_keyword", "contiene_excluida", "en_rubro_objetivo", "score", "prioridad"):
        assert column in result.columns


def test_compile_keywords_merges_a_word_with_its_plural() -> None:
    patterns = compile_keywords(["Obra", "obras", " reparación ", "reparaciones", ""])

    assert list(patterns) == ["obra", "reparacion"]
    assert count_keywords(normalize_text("Obras y reparaciones varias"), patterns) == 2


def test_custom_profile_changes_keywords_regions_and_points() -> None:
    config = ScoringConfig(
        keywords=["software", "licencia"],
        excluded_keywords=[],
        priority_regions=["Biobío"],
        points_keyword=40,
        points_region=25,
    )

    con_perfil = score_licitaciones(
        pd.DataFrame([_licitacion("Licencias de software", region_unidad="Región del Biobío")]), config=config
    ).iloc[0]
    con_defecto = _score("Licencias de software", region_unidad="Región del Biobío")

    assert con_perfil["score"] == 40 + 20 + 25
    assert con_perfil["prioridad"] == "alta"
    assert con_defecto["score"] == 0


def test_reference_date_decides_whether_a_licitation_is_still_open() -> None:
    data = pd.DataFrame([_licitacion("Compra de insumos", fecha_cierre="2026-04-10T15:00:00")])

    antes = score_licitaciones(data, reference_date="2026-04-01").iloc[0]
    despues = score_licitaciones(data, reference_date="2026-05-01").iloc[0]

    assert antes["score"] == 15
    assert despues["score"] == 0


def test_load_scoring_config_reads_json_and_keeps_defaults(tmp_path) -> None:
    path = tmp_path / "perfil.json"
    path.write_text('{"keywords": ["software"], "points_keyword": 50}', encoding="utf-8")

    config = load_scoring_config(path)

    assert config.keywords == ["software"]
    assert config.points_keyword == 50
    assert config.points_region == ScoringConfig().points_region


def test_example_config_file_matches_the_default_profile() -> None:
    assert load_scoring_config("config/scoring.example.json") == ScoringConfig()


def test_unknown_config_field_is_rejected(tmp_path) -> None:
    path = tmp_path / "perfil.json"
    path.write_text('{"palabras": ["software"]}', encoding="utf-8")

    with pytest.raises(ValueError):
        load_scoring_config(path)


def test_target_category_adds_points_ignoring_case_and_accents() -> None:
    config = ScoringConfig(keywords=[], target_categories=["Servicios de construcción y mantenimiento"])
    data = pd.DataFrame(
        [
            _licitacion("Pavimentación de calle", rubro_principal="SERVICIOS DE CONSTRUCCION Y MANTENIMIENTO"),
            _licitacion("Compra de guantes", rubro_principal="Equipamiento y suministros médicos"),
            _licitacion("Sin rubro informado", rubro_principal=None),
        ]
    )

    result = score_licitaciones(data, config=config)

    assert result["en_rubro_objetivo"].tolist() == [True, False, False]
    assert result["score"].tolist() == [30, 0, 0]


def test_without_target_categories_the_category_adds_nothing() -> None:
    row = _score("Compra de insumos", rubro_principal="Servicios de construcción y mantenimiento")

    assert bool(row["en_rubro_objetivo"]) is False
    assert row["score"] == 0
