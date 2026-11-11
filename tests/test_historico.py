from __future__ import annotations

import io

import pandas as pd
import pytest

from app.services.historico import (
    RAW_COLUMNS,
    TENDER_COLUMNS,
    aggregate_tenders,
    monthly_summary,
    read_offer_rows,
)


def _row(**overrides: str) -> dict[str, str]:
    base = {
        "CodigoExterno": "1000-1-LE26",
        "Nombre": " Mantención de equipos ",
        "CodigoEstado": "8",
        "Estado": "Adjudicada",
        "Tipo": "LE",
        "FechaPublicacion": "2026-03-10",
        "FechaCierre": "2026-03-20",
        "NombreOrganismo": "Municipalidad Demo",
        "sector": "Municipalidades",
        "RegionUnidad": "Región del Biobío ",
        "CodigoMoneda": "CLP",
        "MontoEstimado": "15000000",
        "NumeroOferentes": "3",
        "Codigoitem": "1",
        "Rubro1": "SERVICIOS DE CONSTRUCCIÓN Y MANTENIMIENTO",
        "CodigoProveedor": "100",
        "Oferta seleccionada": "No Seleccionada",
    }
    base.update(overrides)
    return base


def _csv(rows: list[dict[str, str]], extra_lines: list[str] | None = None) -> io.BytesIO:
    lines = [";".join(f'"{column}"' for column in RAW_COLUMNS)]
    lines += [";".join(f'"{row[column]}"' for column in RAW_COLUMNS) for row in rows]
    lines += extra_lines or []
    return io.BytesIO("\r\n".join(lines).encode("latin-1"))


def test_read_offer_rows_drops_rows_that_do_not_parse_cleanly() -> None:
    rows = [
        _row(),
        _row(CodigoExterno="texto desplazado"),
        _row(CodigoEstado="Adjudicada"),
        _row(**{"Oferta seleccionada": "2026-03-24"}),
        _row(FechaPublicacion="no es fecha"),
    ]
    shifted_line = ";".join(['"x"'] * (len(RAW_COLUMNS) + 3))

    valid, stats = read_offer_rows(_csv(rows, extra_lines=[shifted_line]))

    assert valid["CodigoExterno"].tolist() == ["1000-1-LE26"]
    assert stats == {"filas_leidas": 6, "filas_validas": 1}


def test_aggregate_tenders_builds_one_row_per_tender_with_its_outcome() -> None:
    rows = pd.DataFrame(
        [
            _row(Codigoitem="1", CodigoProveedor="100"),
            _row(Codigoitem="1", CodigoProveedor="200", **{"Oferta seleccionada": "Seleccionada"}),
            _row(Codigoitem="2", CodigoProveedor="200", **{"Oferta seleccionada": "Seleccionada"}),
            _row(Codigoitem="2", CodigoProveedor="300", Rubro1="OTRO RUBRO"),
            _row(
                CodigoExterno="2000-5-LP26",
                CodigoEstado="7",
                Estado="Desierta",
                MontoEstimado="983,8",
                NumeroOferentes="1",
                CodigoMoneda="CLF",
            ),
        ]
    )

    tenders = aggregate_tenders(rows).set_index("codigo_externo")

    assert list(tenders.reset_index().columns) == TENDER_COLUMNS
    awarded = tenders.loc["1000-1-LE26"]
    assert awarded["nombre"] == "Mantención de equipos"
    assert awarded["region_unidad"] == "Región del Biobío"
    assert awarded["codigo_estado"] == 8
    assert awarded["fecha_publicacion"] == pd.Timestamp("2026-03-10")
    assert awarded["monto_estimado"] == 15_000_000
    assert awarded["rubro_principal"] == "SERVICIOS DE CONSTRUCCIÓN Y MANTENIMIENTO"
    assert awarded["cantidad_items"] == 2
    assert awarded["numero_oferentes"] == 3
    assert awarded["proveedores_adjudicados"] == 1

    deserted = tenders.loc["2000-5-LP26"]
    assert deserted["monto_estimado"] == pytest.approx(983.8)
    assert deserted["proveedores_adjudicados"] == 0


def test_aggregate_tenders_of_no_rows_is_an_empty_frame() -> None:
    tenders = aggregate_tenders(pd.DataFrame(columns=RAW_COLUMNS))

    assert tenders.empty
    assert list(tenders.columns) == TENDER_COLUMNS


def test_monthly_summary_counts_awards_bidders_and_usable_amounts() -> None:
    tenders = pd.DataFrame(
        {
            "fecha_publicacion": pd.to_datetime(["2026-02-03", "2026-02-20", "2026-03-01", "2026-03-15"]),
            "codigo_estado": [8, 7, 8, 8],
            "numero_oferentes": [2, 4, 10, 6],
            "moneda": ["CLP", "CLP", "USD", "CLP"],
            "monto_estimado": [10_000_000, 1, 5_000, 30_000_000],
        }
    )

    summary = monthly_summary(tenders).set_index("mes")

    assert summary.index.tolist() == ["2026-02", "2026-03"]
    assert summary.loc["2026-02", "licitaciones"] == 2
    assert summary.loc["2026-02", "pct_adjudicadas"] == 50
    assert summary.loc["2026-02", "mediana_oferentes"] == 3
    assert summary.loc["2026-02", "con_monto_clp"] == 1
    assert summary.loc["2026-02", "monto_total_mm"] == 10
    assert summary.loc["2026-03", "con_monto_clp"] == 1
    assert summary.loc["2026-03", "mediana_monto_mm"] == 30
