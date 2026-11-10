from __future__ import annotations

import pandas as pd

from app.services.transform import (
    DETAIL_COLUMNS,
    ITEM_COLUMNS,
    SUMMARY_COLUMNS,
    normalize_items,
    normalize_licitacion_detail,
    normalize_licitaciones,
    normalize_licitaciones_summary,
)


LICITACION_COMPLETA = {
    "CodigoExterno": "1000-1-LQ26",
    "Nombre": "  Servicio de datos  ",
    "Descripcion": "  Implementacion BI  ",
    "CodigoEstado": "5",
    "Estado": " Publicada ",
    "FechaCierre": "2026-04-10T15:00:00",
    "Comprador": {
        "CodigoOrganismo": "7001",
        "NombreOrganismo": " Municipalidad Demo ",
        "NombreUnidad": " Secpla ",
        "ComunaUnidad": " Santiago ",
        "RegionUnidad": " Region Metropolitana ",
    },
    "DiasCierreLicitacion": "5",
    "CodigoTipo": "1",
    "Tipo": "LQ",
    "Moneda": "CLP",
    "MontoEstimado": "15000000",
    "VisibilidadMonto": 1,
    "Obras": 0,
    "CantidadReclamos": "2",
    "Modalidad": "30",
    "TipoPago": "1",
    "SubContratacion": "0",
    "TiempoDuracionContrato": "12",
    "Fechas": {
        "FechaCreacion": "2026-04-01T09:00:00",
        "FechaPublicacion": "2026-04-02T10:00:00",
        "FechaAdjudicacion": "2026-04-20T12:00:00",
    },
}


def test_normalize_summary_keeps_only_summary_columns() -> None:
    data = {"Cantidad": 1, "Listado": [LICITACION_COMPLETA]}

    df = normalize_licitaciones_summary(data, fecha_consulta_origen="2026-04-04")

    assert list(df.columns) == SUMMARY_COLUMNS
    assert len(df) == 1
    row = df.iloc[0]
    assert row["codigo_externo"] == "1000-1-LQ26"
    assert row["nombre"] == "Servicio de datos"
    assert row["codigo_estado"] == 5
    assert row["fecha_cierre"] == pd.Timestamp("2026-04-10T15:00:00")
    assert row["fecha_consulta_origen"] == pd.Timestamp("2026-04-04")
    assert isinstance(row["fecha_extraccion"], pd.Timestamp)


def test_normalize_summary_returns_empty_frame_when_api_reports_zero() -> None:
    df = normalize_licitaciones_summary({"Cantidad": 0, "Listado": []})

    assert df.empty
    assert list(df.columns) == SUMMARY_COLUMNS


def test_normalize_licitaciones_wrapper_matches_summary() -> None:
    data = {"Cantidad": 1, "Listado": [LICITACION_COMPLETA]}

    assert list(normalize_licitaciones(data).columns) == SUMMARY_COLUMNS


def test_normalize_detail_cleans_and_types_fields() -> None:
    data = {"Cantidad": 1, "Listado": [LICITACION_COMPLETA]}

    df = normalize_licitacion_detail(data, source_file="1000-1-LQ26.json")

    assert list(df.columns) == DETAIL_COLUMNS
    assert len(df) == 1
    row = df.iloc[0]
    assert row["codigo_externo"] == "1000-1-LQ26"
    assert row["nombre"] == "Servicio de datos"
    assert row["descripcion"] == "Implementacion BI"
    assert row["codigo_estado"] == 5
    assert row["estado"] == "Publicada"
    assert row["organismo_nombre"] == "Municipalidad Demo"
    assert row["region_unidad"] == "Region Metropolitana"
    assert row["monto_estimado"] == 15000000.0
    assert bool(row["visibilidad_monto"]) is True
    assert bool(row["obras"]) is False
    assert row["cantidad_reclamos"] == 2
    assert row["fecha_cierre"] == pd.Timestamp("2026-04-10T15:00:00")
    assert row["fecha_creacion"] == pd.Timestamp("2026-04-01T09:00:00")
    assert row["fecha_publicacion"] == pd.Timestamp("2026-04-02T10:00:00")
    assert row["extraction_status"] == "success"
    assert row["source_file"] == "1000-1-LQ26.json"


def test_normalize_detail_supports_nested_listado_and_estado_as_dict() -> None:
    data = {
        "Listado": {
            "Licitacion": [
                {
                    "CodigoExterno": "2000-3-LE26",
                    "Nombre": "Licitacion detallada",
                    "CodigoEstado": 6,
                    "Estado": {"Estado": "Cerrada"},
                    "Comprador": {"NombreOrganismo": "Hospital Demo"},
                    "Fechas": {
                        "FechaCreacion": "2026-04-03T11:00:00",
                        "FechaCierre": "2026-04-08T16:00:00",
                    },
                }
            ]
        }
    }

    df = normalize_licitacion_detail(data)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["codigo_externo"] == "2000-3-LE26"
    assert row["estado"] == "Cerrada"
    assert row["organismo_nombre"] == "Hospital Demo"
    assert row["fecha_cierre"] == pd.Timestamp("2026-04-08T16:00:00")
    assert row["fecha_creacion"] == pd.Timestamp("2026-04-03T11:00:00")


def test_normalize_detail_keeps_a_row_for_failed_extractions() -> None:
    df = normalize_licitacion_detail({}, extraction_status="error", code_override="9999-1-LE26")

    assert len(df) == 1
    assert df.iloc[0]["codigo_externo"] == "9999-1-LE26"
    assert df.iloc[0]["extraction_status"] == "error"


def test_normalize_items_extracts_item_rows() -> None:
    data = {
        "Listado": [
            {
                "CodigoExterno": "3000-1-LP26",
                "Items": {
                    "Listado": {
                        "Item": [
                            {
                                "Correlativo": 1,
                                "CodigoProducto": "80101500",
                                "CodigoCategoria": "80100000",
                                "Categoria": "Servicios profesionales",
                                "NombreProducto": "Consultoria",
                                "Descripcion": "Analisis de datos",
                                "UnidadMedida": "Unidad",
                                "Cantidad": "2",
                            }
                        ]
                    }
                },
            }
        ]
    }

    df = normalize_items(data)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["codigo_externo"] == "3000-1-LP26"
    assert row["correlativo"] == 1
    assert row["codigo_producto"] == "80101500"
    assert row["codigo_categoria"] == "80100000"
    assert row["categoria"] == "Servicios profesionales"
    assert row["nombre_producto"] == "Consultoria"
    assert row["descripcion_item"] == "Analisis de datos"
    assert row["unidad_medida"] == "Unidad"
    assert row["cantidad"] == 2.0


def test_normalize_items_returns_empty_dataframe_when_no_items_exist() -> None:
    data = {
        "Listado": [
            {
                "CodigoExterno": "4000-1-LE26",
                "Nombre": "Sin items",
            }
        ]
    }

    df = normalize_items(data)

    assert df.empty
    assert list(df.columns) == ITEM_COLUMNS
