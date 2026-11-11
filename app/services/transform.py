"""Normalization helpers for Mercado Publico licitation payloads."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.services.keywords import (
    CONSTRUCCION_KEYWORDS,
    EXCLUDED_KEYWORDS,
    INDUSTRIAL_KEYWORDS,
    SERVICIO_KEYWORDS,
    contains_any_keyword,
    normalize_text,
)


SUMMARY_COLUMNS = [
    "codigo_externo",
    "nombre",
    "codigo_estado",
    "fecha_cierre",
    "fecha_extraccion",
    "fecha_consulta_origen",
    "source_file",
]

DETAIL_COLUMNS = [
    "codigo_externo",
    "nombre",
    "descripcion",
    "codigo_estado",
    "estado",
    "codigo_tipo",
    "tipo",
    "tipo_convocatoria",
    "fecha_cierre",
    "fecha_creacion",
    "fecha_publicacion",
    "fecha_adjudicacion",
    "fecha_estimada_adjudicacion",
    "fecha_inicio",
    "fecha_final",
    "fecha_visita_terreno",
    "fecha_entrega_antecedentes",
    "organismo_codigo",
    "organismo_nombre",
    "rut_unidad",
    "unidad_codigo",
    "unidad_nombre",
    "direccion_unidad",
    "comuna_unidad",
    "region_unidad",
    "rut_usuario",
    "codigo_usuario",
    "nombre_usuario",
    "cargo_usuario",
    "moneda",
    "monto_estimado",
    "visibilidad_monto",
    "estimacion",
    "fuente_financiamiento",
    "modalidad",
    "tipo_pago",
    "contrato",
    "obras",
    "subcontratacion",
    "tiempo_duracion_contrato",
    "tipo_duracion_contrato",
    "unidad_tiempo_duracion_contrato",
    "justificacion_monto_estimado",
    "dias_cierre_licitacion",
    "informada",
    "etapas",
    "estado_etapas",
    "toma_razon",
    "estado_publicidad_ofertas",
    "justificacion_publicidad",
    "cantidad_reclamos",
    "prohibicion_contratacion",
    "extension_plazo",
    "es_base_tipo",
    "es_renovable",
    "nombre_responsable_pago",
    "email_responsable_pago",
    "nombre_responsable_contrato",
    "email_responsable_contrato",
    "fono_responsable_contrato",
    "adjudicacion_tipo",
    "adjudicacion_fecha",
    "adjudicacion_numero",
    "adjudicacion_numero_oferentes",
    "adjudicacion_url_acta",
    "fecha_extraccion",
    "source_file",
    "extraction_status",
]

ITEM_COLUMNS = [
    "codigo_externo",
    "correlativo",
    "codigo_producto",
    "codigo_categoria",
    "categoria",
    "nombre_producto",
    "descripcion_item",
    "unidad_medida",
    "cantidad",
    "rut_proveedor_adjudicado",
    "nombre_proveedor_adjudicado",
    "cantidad_adjudicada",
    "monto_unitario",
    "source_file",
]

DETAIL_DATE_COLUMNS = [
    "fecha_cierre",
    "fecha_creacion",
    "fecha_publicacion",
    "fecha_adjudicacion",
    "fecha_estimada_adjudicacion",
    "fecha_inicio",
    "fecha_final",
    "fecha_visita_terreno",
    "fecha_entrega_antecedentes",
]

STATE_MAP = {
    5: "Publicada",
    6: "Cerrada",
    7: "Desierta",
    8: "Adjudicada",
    15: "Revocada o finalizada no vigente",
    16: "Suspendida",
    18: "Revocada",
    19: "Suspendida",
}

def normalize_licitaciones_summary(
    data: dict[str, Any],
    fecha_consulta_origen: str | None = None,
    source_file: str | Path | None = None,
    extraction_timestamp: datetime | None = None,
) -> pd.DataFrame:
    """Normalize a summary licitation payload into a DataFrame."""

    extraction_value = pd.Timestamp(extraction_timestamp or datetime.now())
    rows: list[dict[str, Any]] = []

    for item in _extract_licitaciones(data):
        fechas = _as_dict(item.get("Fechas"))
        rows.append(
            {
                "codigo_externo": _clean_text(item.get("CodigoExterno")),
                "nombre": _clean_text(item.get("Nombre")),
                "codigo_estado": _to_int(item.get("CodigoEstado")),
                "fecha_cierre": _to_datetime(item.get("FechaCierre") or fechas.get("FechaCierre")),
                "fecha_extraccion": extraction_value,
                "fecha_consulta_origen": _to_datetime(fecha_consulta_origen) if fecha_consulta_origen else None,
                "source_file": _clean_text(source_file),
            }
        )

    if not rows:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    frame = pd.DataFrame(rows)
    return frame.reindex(columns=SUMMARY_COLUMNS)


def normalize_licitacion_detail(
    data: dict[str, Any],
    source_file: str | Path | None = None,
    extraction_status: str = "success",
    extraction_timestamp: datetime | None = None,
    code_override: str | None = None,
) -> pd.DataFrame:
    """Normalize a detailed licitation payload into a one-row DataFrame."""

    extraction_value = pd.Timestamp(extraction_timestamp or datetime.now())
    rows: list[dict[str, Any]] = []

    for item in _extract_licitaciones(data):
        fechas = _as_dict(item.get("Fechas"))
        comprador = _as_dict(item.get("Comprador"))
        adjudicacion = _as_dict(item.get("Adjudicacion"))

        rows.append(
            {
                "codigo_externo": _clean_text(item.get("CodigoExterno")) or _clean_text(code_override),
                "nombre": _clean_text(item.get("Nombre")),
                "descripcion": _clean_text(item.get("Descripcion")),
                "codigo_estado": _to_int(item.get("CodigoEstado") or _safe_get(item, "Estado", "Codigo")),
                "estado": _extract_estado(item.get("Estado")),
                "codigo_tipo": _to_int(item.get("CodigoTipo")),
                "tipo": _clean_text(item.get("Tipo")),
                "tipo_convocatoria": _to_int(item.get("TipoConvocatoria")),
                "fecha_cierre": _to_datetime(item.get("FechaCierre") or fechas.get("FechaCierre")),
                "fecha_creacion": _to_datetime(item.get("FechaCreacion") or fechas.get("FechaCreacion")),
                "fecha_publicacion": _to_datetime(fechas.get("FechaPublicacion")),
                "fecha_adjudicacion": _to_datetime(fechas.get("FechaAdjudicacion") or adjudicacion.get("Fecha")),
                "fecha_estimada_adjudicacion": _to_datetime(fechas.get("FechaEstimadaAdjudicacion")),
                "fecha_inicio": _to_datetime(fechas.get("FechaInicio")),
                "fecha_final": _to_datetime(fechas.get("FechaFinal")),
                "fecha_visita_terreno": _to_datetime(fechas.get("FechaVisitaTerreno")),
                "fecha_entrega_antecedentes": _to_datetime(fechas.get("FechaEntregaAntecedentes")),
                "organismo_codigo": _clean_text(comprador.get("CodigoOrganismo")),
                "organismo_nombre": _clean_text(comprador.get("NombreOrganismo")),
                "rut_unidad": _clean_text(comprador.get("RutUnidad")),
                "unidad_codigo": _clean_text(comprador.get("CodigoUnidad")),
                "unidad_nombre": _clean_text(comprador.get("NombreUnidad")),
                "direccion_unidad": _clean_text(comprador.get("DireccionUnidad")),
                "comuna_unidad": _clean_text(comprador.get("ComunaUnidad")),
                "region_unidad": _clean_text(comprador.get("RegionUnidad")),
                "rut_usuario": _clean_text(comprador.get("RutUsuario")),
                "codigo_usuario": _clean_text(comprador.get("CodigoUsuario")),
                "nombre_usuario": _clean_text(comprador.get("NombreUsuario")),
                "cargo_usuario": _clean_text(comprador.get("CargoUsuario")),
                "moneda": _clean_text(item.get("Moneda")),
                "monto_estimado": _to_numeric(item.get("MontoEstimado")),
                "visibilidad_monto": _to_bool(item.get("VisibilidadMonto")),
                "estimacion": _clean_text(item.get("Estimacion")),
                "fuente_financiamiento": _clean_text(item.get("FuenteFinanciamiento")),
                "modalidad": _to_int(item.get("Modalidad")),
                "tipo_pago": _to_int(item.get("TipoPago")),
                "contrato": _clean_text(item.get("Contrato")),
                "obras": _to_bool(item.get("Obras")),
                "subcontratacion": _to_bool(item.get("SubContratacion")),
                "tiempo_duracion_contrato": _to_int(item.get("TiempoDuracionContrato")),
                "tipo_duracion_contrato": _clean_text(item.get("TipoDuracionContrato")),
                "unidad_tiempo_duracion_contrato": _clean_text(item.get("UnidadTiempoDuracionContrato")),
                "justificacion_monto_estimado": _clean_text(item.get("JustificacionMontoEstimado")),
                "dias_cierre_licitacion": _to_int(item.get("DiasCierreLicitacion")),
                "informada": _to_bool(item.get("Informada")),
                "etapas": _to_int(item.get("Etapas")),
                "estado_etapas": _to_int(item.get("EstadoEtapas")),
                "toma_razon": _to_bool(item.get("TomaRazon")),
                "estado_publicidad_ofertas": _clean_text(item.get("EstadoPublicidadOfertas")),
                "justificacion_publicidad": _clean_text(item.get("JustificacionPublicidad")),
                "cantidad_reclamos": _to_int(item.get("CantidadReclamos")),
                "prohibicion_contratacion": _to_bool(item.get("ProhibicionContratacion")),
                "extension_plazo": _to_bool(item.get("ExtensionPlazo")),
                "es_base_tipo": _to_bool(item.get("EsBaseTipo")),
                "es_renovable": _to_bool(item.get("EsRenovable")),
                "nombre_responsable_pago": _clean_text(item.get("NombreResponsablePago")),
                "email_responsable_pago": _clean_text(item.get("EmailResponsablePago")),
                "nombre_responsable_contrato": _clean_text(item.get("NombreResponsableContrato")),
                "email_responsable_contrato": _clean_text(item.get("EmailResponsableContrato")),
                "fono_responsable_contrato": _clean_text(item.get("FonoResponsableContrato")),
                "adjudicacion_tipo": _clean_text(adjudicacion.get("Tipo")),
                "adjudicacion_fecha": _to_datetime(adjudicacion.get("Fecha")),
                "adjudicacion_numero": _clean_text(adjudicacion.get("Numero")),
                "adjudicacion_numero_oferentes": _to_int(adjudicacion.get("NumeroOferentes")),
                "adjudicacion_url_acta": _clean_text(adjudicacion.get("UrlActa")),
                "fecha_extraccion": extraction_value,
                "source_file": _clean_text(source_file),
                "extraction_status": extraction_status,
            }
        )

    if not rows and code_override:
        rows.append(
            {
                "codigo_externo": _clean_text(code_override),
                "fecha_extraccion": extraction_value,
                "source_file": _clean_text(source_file),
                "extraction_status": extraction_status,
            }
        )

    if not rows:
        return pd.DataFrame(columns=DETAIL_COLUMNS)

    frame = pd.DataFrame(rows)
    return frame.reindex(columns=DETAIL_COLUMNS)


def normalize_licitacion_items(
    data: dict[str, Any],
    source_file: str | Path | None = None,
) -> pd.DataFrame:
    """Normalize licitation items from a detailed payload into a DataFrame."""

    rows: list[dict[str, Any]] = []

    for licitacion in _extract_licitaciones(data):
        codigo_externo = _clean_text(licitacion.get("CodigoExterno"))
        for item in _extract_items(licitacion):
            adjudicacion_item = _as_dict(item.get("Adjudicacion"))
            rows.append(
                {
                    "codigo_externo": codigo_externo,
                    "correlativo": _to_int(item.get("Correlativo")),
                    "codigo_producto": _clean_text(item.get("CodigoProducto")),
                    "codigo_categoria": _clean_text(item.get("CodigoCategoria")),
                    "categoria": _clean_text(
                        item.get("Categoria")
                        or item.get("NombreCategoria")
                        or item.get("CategoriaProducto")
                    ),
                    "nombre_producto": _clean_text(item.get("NombreProducto") or item.get("Producto")),
                    "descripcion_item": _clean_text(
                        item.get("Descripcion")
                        or item.get("DescripcionItem")
                        or item.get("EspecificacionComprador")
                    ),
                    "unidad_medida": _clean_text(
                        item.get("UnidadMedida")
                        or item.get("Unidad")
                        or item.get("NombreUnidad")
                    ),
                    "cantidad": _to_numeric(item.get("Cantidad")),
                    "rut_proveedor_adjudicado": _clean_text(
                        item.get("RutProveedorAdjudicado")
                        or adjudicacion_item.get("RutProveedor")
                    ),
                    "nombre_proveedor_adjudicado": _clean_text(
                        item.get("NombreProveedorAdjudicado")
                        or adjudicacion_item.get("NombreProveedor")
                    ),
                    "cantidad_adjudicada": _to_numeric(
                        item.get("CantidadAdjudicada")
                        or adjudicacion_item.get("CantidadAdjudicada")
                    ),
                    "monto_unitario": _to_numeric(
                        item.get("MontoUnitario")
                        or adjudicacion_item.get("MontoUnitario")
                    ),
                    "source_file": _clean_text(source_file),
                }
            )

    if not rows:
        return pd.DataFrame(columns=ITEM_COLUMNS)

    frame = pd.DataFrame(rows)
    return frame.reindex(columns=ITEM_COLUMNS)


def normalize_detail_records(detail_payloads: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize multiple detailed payloads into detail and items DataFrames."""

    detail_frames: list[pd.DataFrame] = []
    item_frames: list[pd.DataFrame] = []

    for entry in detail_payloads:
        payload = entry.get("payload", entry)
        source_file = entry.get("source_file")
        extraction_status = entry.get("extraction_status", "success")
        code = entry.get("code")
        extraction_timestamp = entry.get("fecha_extraccion")

        detail_frames.append(
            normalize_licitacion_detail(
                payload,
                source_file=source_file,
                extraction_status=extraction_status,
                extraction_timestamp=extraction_timestamp,
                code_override=code,
            )
        )

        if extraction_status == "success":
            item_frames.append(normalize_licitacion_items(payload, source_file=source_file))

    details_df = pd.concat(detail_frames, ignore_index=True) if detail_frames else pd.DataFrame(columns=DETAIL_COLUMNS)
    items_df = pd.concat(item_frames, ignore_index=True) if item_frames else pd.DataFrame(columns=ITEM_COLUMNS)

    if not details_df.empty:
        details_df = details_df.drop_duplicates(subset=["codigo_externo"], keep="last").reindex(columns=DETAIL_COLUMNS)

    if not items_df.empty:
        items_df = items_df.reindex(columns=ITEM_COLUMNS)

    return details_df, items_df


def build_analysis_ready_licitaciones(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build an analysis-ready licitations DataFrame with derived columns."""

    if dataframe.empty:
        return dataframe.copy()

    frame = dataframe.copy()
    for column in DETAIL_DATE_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")

    frame["estado_nombre_mapeado"] = frame["codigo_estado"].map(STATE_MAP)
    frame["es_publicada"] = frame["codigo_estado"].eq(5)
    frame["es_adjudicada"] = frame["codigo_estado"].eq(8)
    frame["es_cerrada"] = frame["codigo_estado"].eq(6)
    frame["es_revocada"] = frame["codigo_estado"].isin([15, 18])
    frame["es_suspendida"] = frame["codigo_estado"].eq(19)
    frame["anio_fecha_publicacion"] = frame["fecha_publicacion"].dt.year
    frame["mes_fecha_publicacion"] = frame["fecha_publicacion"].dt.month
    frame["anio_fecha_cierre"] = frame["fecha_cierre"].dt.year
    frame["mes_fecha_cierre"] = frame["fecha_cierre"].dt.month
    frame["dias_hasta_cierre"] = (frame["fecha_cierre"] - pd.Timestamp(datetime.now())).dt.days

    nombre = frame["nombre"].fillna("")
    descripcion = frame["descripcion"].fillna("")
    frame["texto_busqueda"] = (nombre + " " + descripcion).str.strip()

    normalized_text = frame["texto_busqueda"].map(normalize_text)
    frame["es_industrial_keyword"] = normalized_text.map(lambda value: contains_any_keyword(value, INDUSTRIAL_KEYWORDS))
    frame["es_construccion_keyword"] = normalized_text.map(lambda value: contains_any_keyword(value, CONSTRUCCION_KEYWORDS))
    frame["es_servicio_keyword"] = normalized_text.map(lambda value: contains_any_keyword(value, SERVICIO_KEYWORDS))
    frame["contiene_excluida"] = normalized_text.map(lambda value: contains_any_keyword(value, EXCLUDED_KEYWORDS))
    frame["prioridad_inicial"] = frame.apply(_compute_prioridad_inicial, axis=1)

    return frame


def build_analysis_ready_items(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return an analysis-ready items DataFrame with cleaned types."""

    if dataframe.empty:
        return dataframe.copy()

    frame = dataframe.copy()
    for column in ["correlativo"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ["cantidad", "cantidad_adjudicada", "monto_unitario"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def normalize_licitaciones(data: dict[str, Any]) -> pd.DataFrame:
    """Compatibility wrapper for the existing project."""

    return normalize_licitaciones_summary(data)


def normalize_items(data: dict[str, Any]) -> pd.DataFrame:
    """Compatibility wrapper for the existing project."""

    return normalize_licitacion_items(data)


def _extract_licitaciones(data: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []

    if data.get("Cantidad") == 0:
        return []

    listado = data.get("Listado")
    if isinstance(listado, list):
        return [item for item in listado if isinstance(item, dict)]

    if isinstance(listado, dict):
        for key in ("Licitacion", "Licitaciones", "Listado"):
            nested = listado.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
            if isinstance(nested, dict):
                return [nested]

    if _looks_like_licitacion(data):
        return [data]

    return []


def _extract_items(licitacion: dict[str, Any]) -> list[dict[str, Any]]:
    items = licitacion.get("Items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]

    if not isinstance(items, dict):
        return []

    listado = items.get("Listado")
    if isinstance(listado, list):
        return [item for item in listado if isinstance(item, dict)]

    if isinstance(listado, dict):
        for key in ("Item", "Items", "item"):
            nested = listado.get(key)
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
            if isinstance(nested, dict):
                return [nested]
        return [listado]

    for key in ("Item", "Items", "item"):
        nested = items.get(key)
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        if isinstance(nested, dict):
            return [nested]

    return []


def _looks_like_licitacion(data: dict[str, Any]) -> bool:
    return any(key in data for key in ("CodigoExterno", "Nombre", "CodigoEstado", "Comprador", "Fechas"))


def _extract_estado(value: Any) -> str | None:
    if isinstance(value, dict):
        return _clean_text(value.get("Estado") or value.get("Nombre"))
    return _clean_text(value)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_get(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_datetime(value: Any) -> pd.Timestamp | None:
    if value in (None, ""):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed


def _to_numeric(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    normalized = str(value).strip().replace(" ", "")
    if not normalized:
        return None

    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")

    parsed = pd.to_numeric(normalized, errors="coerce")
    if pd.isna(parsed):
        return None
    return float(parsed)


def _to_int(value: Any) -> int | None:
    numeric = _to_numeric(value)
    if pd.isna(numeric) or numeric is None:
        return None
    return int(numeric)


def _to_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "si", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    return None


def _compute_prioridad_inicial(row: pd.Series) -> str:
    if row.get("contiene_excluida"):
        return "baja"
    if row.get("es_publicada") and (row.get("es_industrial_keyword") or row.get("es_construccion_keyword")):
        return "alta"
    if row.get("es_publicada") and row.get("es_servicio_keyword"):
        return "media"
    return "baja"
