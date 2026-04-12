"""Extraction services for Mercado Publico API payloads."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.api.client import MercadoPublicoAPIClient
from app.config import Settings, get_settings


def fetch_licitaciones_by_date(
    target_date: str,
    estado: str | None = None,
    client: MercadoPublicoAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch licitations by date from the Mercado Publico API."""

    active_client = client or MercadoPublicoAPIClient()
    return active_client.get_licitaciones_by_date(target_date=target_date, estado=estado)


def fetch_licitaciones_today(
    estado: str | None = None,
    client: MercadoPublicoAPIClient | None = None,
) -> dict[str, Any]:
    """Fetch licitations for the current day from the Mercado Publico API."""

    active_client = client or MercadoPublicoAPIClient()
    return active_client.get_licitaciones_today(estado=estado)


def save_raw_payload(
    payload: dict[str, Any],
    prefix: str,
    settings: Settings | None = None,
    timestamp: datetime | None = None,
) -> Path:
    """Persist the raw API payload to the configured `data/raw` directory."""

    active_settings = settings or get_settings()
    active_timestamp = timestamp or datetime.now()
    safe_prefix = _sanitize_filename_part(prefix)
    filename = f"{safe_prefix}_{active_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    output_path = active_settings.raw_data_dir / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return output_path


def _sanitize_filename_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value).strip("_")
