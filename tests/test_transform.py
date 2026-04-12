from __future__ import annotations

import pandas as pd

from app.services.transform import normalize_items, normalize_licitaciones


def test_normalize_licitaciones_supports_summary_response() -> None:
    data = {
        "Cantidad": 1,
        "Listado": [
            {
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
        ],
    }

    df = normalize_licitaciones(data)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["codigo_externo"] == "1000-1-LQ26"
    assert row["nombre"] == "Servicio de datos"
    assert row["descripcion"] == "Implementacion BI"
    assert row["codigo_estado"] == 5
    assert row["estado"] == "Publicada"
    assert row["organismo_nombre"] == "Municipalidad Demo"
    assert row["monto_estimado"] == 15000000.0
    assert row["visibilidad_monto"] is True
    assert row["obras"] is False
    assert isinstance(row["fecha_cierre"], pd.Timestamp)
    assert isinstance(row["fecha_creacion"], pd.Timestamp)
    assert isinstance(row["fecha_extraccion"], pd.Timestamp)


def test_normalize_licitaciones_supports_detailed_response_with_nested_listado() -> None:
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

    df = normalize_licitaciones(data)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["codigo_externo"] == "2000-3-LE26"
    assert row["estado"] == "Cerrada"
    assert row["organismo_nombre"] == "Hospital Demo"
    assert row["fecha_cierre"] == pd.Timestamp("2026-04-08T16:00:00")
    assert row["fecha_creacion"] == pd.Timestamp("2026-04-03T11:00:00")


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
    assert list(df.columns) == [
        "codigo_externo",
        "correlativo",
        "codigo_producto",
        "codigo_categoria",
        "categoria",
        "nombre_producto",
        "descripcion_item",
        "unidad_medida",
        "cantidad",
    ]
