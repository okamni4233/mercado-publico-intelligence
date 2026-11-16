from __future__ import annotations

import pandas as pd

from app.services.filters import filter_licitaciones


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "codigo_externo": "A",
                "nombre": "Mantención de caminos",
                "descripcion": "Obras viales",
                "region_unidad": "Región de Antofagasta",
                "estado": "Publicada",
                "tipo": "LE",
                "rubro_principal": "Servicios de construcción y mantenimiento",
                "monto_estimado": 50_000_000,
            },
            {
                "codigo_externo": "B",
                "nombre": "Insumos médicos",
                "descripcion": "Guantes y jeringas",
                "region_unidad": "Región del Biobío",
                "estado": "Adjudicada",
                "tipo": "LP",
                "rubro_principal": "Equipamiento y suministros médicos",
                "monto_estimado": 5_000_000,
            },
            {
                "codigo_externo": "C",
                "nombre": "Servicio de aseo",
                "descripcion": None,
                "region_unidad": "Región del Biobío",
                "estado": "Publicada",
                "tipo": "LE",
                "rubro_principal": "Servicios de limpieza industrial",
                "monto_estimado": None,
            },
        ]
    )


def _codes(df: pd.DataFrame) -> list[str]:
    return df["codigo_externo"].tolist()


def test_without_filters_returns_everything() -> None:
    assert _codes(filter_licitaciones(_frame())) == ["A", "B", "C"]


def test_empty_selections_are_ignored() -> None:
    assert _codes(filter_licitaciones(_frame(), regiones=[], estados=[], texto="  ")) == ["A", "B", "C"]


def test_filters_are_combined() -> None:
    result = filter_licitaciones(_frame(), regiones=["Región del Biobío"], estados=["Publicada"])

    assert _codes(result) == ["C"]


def test_amount_range_drops_rows_without_amount() -> None:
    assert _codes(filter_licitaciones(_frame(), monto_minimo=1_000_000)) == ["A", "B"]
    assert _codes(filter_licitaciones(_frame(), monto_minimo=1_000_000, monto_maximo=10_000_000)) == ["B"]


def test_text_search_ignores_case_and_accents_and_reads_the_description() -> None:
    assert _codes(filter_licitaciones(_frame(), texto="MANTENCION")) == ["A"]
    assert _codes(filter_licitaciones(_frame(), texto="jeringas")) == ["B"]


def test_filter_on_a_missing_column_is_ignored() -> None:
    frame = _frame().drop(columns="rubro_principal")

    assert _codes(filter_licitaciones(frame, rubros=["Cualquiera"])) == ["A", "B", "C"]
