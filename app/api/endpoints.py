"""Endpoint builders for Mercado Publico public services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

LICITACIONES_RESOURCE = "licitaciones.json"
ORDENES_COMPRA_RESOURCE = "ordenesdecompra.json"


def format_api_date(value: date | datetime | str) -> str:
    """Convert a supported value into the API expected date format ddmmaaaa."""
    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return value.strftime("%d%m%Y")

    normalized = value.strip()
    if len(normalized) == 8 and normalized.isdigit():
        return normalized

    try:
        parsed = datetime.fromisoformat(normalized).date()
    except ValueError as exc:
        raise ValueError("Date must be a date object, ISO date string, or ddmmaaaa") from exc
    return parsed.strftime("%d%m%Y")


@dataclass(frozen=True)
class EndpointSpec:
    """Represents an endpoint resource and query parameters."""

    resource: str
    params: dict[str, Any]


def licitaciones_today(estado: str | None = None) -> EndpointSpec:
    params: dict[str, Any] = {}
    if estado:
        params["estado"] = estado
    return EndpointSpec(resource=LICITACIONES_RESOURCE, params=params)


def licitaciones_by_date(target_date: date | datetime | str, estado: str | None = None) -> EndpointSpec:
    params: dict[str, Any] = {"fecha": format_api_date(target_date)}
    if estado:
        params["estado"] = estado
    return EndpointSpec(resource=LICITACIONES_RESOURCE, params=params)


def licitacion_by_code(codigo: str) -> EndpointSpec:
    return EndpointSpec(resource=LICITACIONES_RESOURCE, params={"codigo": codigo})


def licitaciones_by_organismo(
    target_date: date | datetime | str,
    codigo_organismo: str,
    estado: str | None = None,
) -> EndpointSpec:
    params: dict[str, Any] = {
        "fecha": format_api_date(target_date),
        "CodigoOrganismo": codigo_organismo,
    }
    if estado:
        params["estado"] = estado
    return EndpointSpec(resource=LICITACIONES_RESOURCE, params=params)


def ordenes_compra_by_date(target_date: date | datetime | str, estado: str | None = None) -> EndpointSpec:
    """Prepared for future expansion to purchase orders."""
    params: dict[str, Any] = {"fecha": format_api_date(target_date)}
    if estado:
        params["estado"] = estado
    return EndpointSpec(resource=ORDENES_COMPRA_RESOURCE, params=params)
