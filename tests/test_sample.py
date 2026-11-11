from __future__ import annotations

import json

import pandas as pd

from app.services.sample import SAMPLE_COLUMNS, build_public_sample, main_category, redact_contact_details


PERSONAL_COLUMNS = {
    "nombre_usuario",
    "cargo_usuario",
    "rut_usuario",
    "codigo_usuario",
    "nombre_responsable_pago",
    "email_responsable_pago",
    "nombre_responsable_contrato",
    "email_responsable_contrato",
    "fono_responsable_contrato",
    "direccion_unidad",
}


def test_redacts_emails_ruts_and_phone_numbers() -> None:
    text = "Consultas a juan.perez@hospital.cl, fono +56 9 8765 4321 o 41 2345678. RUT 12.345.678-9."

    redacted = redact_contact_details(text)

    assert redacted == "Consultas a [correo], fono [telefono] o [telefono]. RUT [rut]."


def test_redaction_keeps_years_and_amounts() -> None:
    text = "Servicio de aseo periodo 2025-2026 por $ 15.000.000 para 120 funcionarios"

    assert redact_contact_details(text) == text


def test_redaction_passes_missing_values_through() -> None:
    assert redact_contact_details(None) is None
    assert redact_contact_details(float("nan")) is None


def test_main_category_takes_the_most_frequent_top_level_category() -> None:
    items = pd.DataFrame(
        {
            "codigo_externo": ["A", "A", "A", "B"],
            "categoria": [
                "Equipamiento médico / Insumos / Guantes",
                "Equipamiento médico / Insumos / Jeringas",
                "Servicios de transporte / Fletes / Carga",
                None,
            ],
        }
    )

    result = main_category(items).set_index("codigo_externo")

    assert result.loc["A", "rubro_principal"] == "Equipamiento médico"
    assert result.loc["A", "cantidad_items"] == 3
    assert pd.isna(result.loc["B", "rubro_principal"])
    assert result.loc["B", "cantidad_items"] == 1


def test_public_sample_has_no_personal_columns_nor_free_text_description(tmp_path) -> None:
    payload = {
        "Cantidad": 1,
        "Listado": [
            {
                "CodigoExterno": "1000-1-LE26",
                "Nombre": "Mantención de equipos, consultas a compras@municipio.cl",
                "Descripcion": "Contactar a Tercera Persona, encargada del contrato",
                "CodigoEstado": 5,
                "Estado": "Publicada",
                "Tipo": "LE",
                "Moneda": "CLP",
                "MontoEstimado": 20000000,
                "Comprador": {
                    "NombreOrganismo": "Municipalidad Demo",
                    "RegionUnidad": "Región del Biobío",
                    "ComunaUnidad": "Concepción",
                    "NombreUsuario": "Persona De Prueba",
                    "CargoUsuario": "Jefa de compras",
                    "RutUsuario": "11.111.111-1",
                },
                "NombreResponsableContrato": "Otra Persona",
                "EmailResponsableContrato": "otra@municipio.cl",
                "Fechas": {"FechaPublicacion": "2026-04-01T10:00:00", "FechaCierre": "2026-04-10T15:00:00"},
                "Items": {"Listado": [{"Correlativo": 1, "Categoria": "Servicios de mantenimiento / Equipos"}]},
            }
        ],
    }
    (tmp_path / "1000-1-LE26.json").write_text(json.dumps(payload), encoding="utf-8")

    sample = build_public_sample(tmp_path)

    assert list(sample.columns) == SAMPLE_COLUMNS
    assert PERSONAL_COLUMNS.isdisjoint(sample.columns)
    row = sample.iloc[0]
    assert row["organismo_nombre"] == "Municipalidad Demo"
    assert row["rubro_principal"] == "Servicios de mantenimiento"
    assert row["cantidad_items"] == 1
    assert row["nombre"] == "Mantención de equipos, consultas a [correo]"
    assert "descripcion" not in sample.columns
    flattened = " ".join(str(value) for value in row.to_list())
    for secret in ("Persona De Prueba", "Otra Persona", "Tercera Persona", "otra@municipio.cl", "11.111.111-1", "compras@municipio.cl"):
        assert secret not in flattened


def test_public_sample_of_an_empty_folder_is_an_empty_frame(tmp_path) -> None:
    sample = build_public_sample(tmp_path)

    assert sample.empty
    assert list(sample.columns) == SAMPLE_COLUMNS
