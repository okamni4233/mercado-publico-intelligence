"""Normalized analytical models."""

from __future__ import annotations

from pydantic import BaseModel


class NormalizedLicitacion(BaseModel):
    """Target analytical schema for licitation records."""

    codigo_externo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    fecha_creacion: str | None = None
    fecha_cierre: str | None = None
    estado_codigo: str | None = None
    estado_nombre: str | None = None
    organismo_nombre: str | None = None
    organismo_codigo: str | None = None
    region: str | None = None
    comprador: str | None = None
    proveedor_relacionado_si_existe: str | None = None
    monto_estimado: float | None = None
    moneda: str | None = None
    categoria: str | None = None
    url_licitacion: str | None = None
    keyword_match: str | None = None
    score_oportunidad: float | None = None
    fecha_extraccion: str | None = None
