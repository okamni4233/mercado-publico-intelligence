"""Bulk extraction services for Mercado Publico licitations."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.api.client import MercadoPublicoAPIClient
from app.config import Settings, get_settings
from app.services.transform import normalize_licitaciones_summary


def fetch_licitaciones_range(
    start_date: str,
    end_date: str,
    sleep_seconds: float = 0.5,
    estado: str | None = None,
    client: MercadoPublicoAPIClient | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Fetch summary licitations day by day for a date range."""

    active_settings = settings or get_settings()
    active_client = client or MercadoPublicoAPIClient(settings=active_settings)
    logger = _get_bulk_logger(active_settings)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    if end_dt < start_dt:
        raise ValueError("end_date must be greater than or equal to start_date")

    results: list[dict[str, Any]] = []
    current_date = start_dt

    while current_date <= end_dt:
        date_str = current_date.isoformat()
        timestamp = datetime.now()
        try:
            payload = active_client.get_licitaciones_by_date(target_date=date_str, estado=estado)
            raw_path = _save_json(
                payload,
                active_settings.raw_data_dir / f"licitaciones_raw_{date_str}_{timestamp.strftime('%Y%m%d_%H%M%S')}.json",
            )
            cantidad = _count_summary_records(payload)
            results.append(
                {
                    "date": date_str,
                    "payload": payload,
                    "raw_path": raw_path,
                    "cantidad": cantidad,
                    "success": True,
                    "error": None,
                    "fecha_extraccion": timestamp,
                }
            )
        except Exception as exc:
            logger.exception("Daily fetch failed for %s", date_str)
            results.append(
                {
                    "date": date_str,
                    "payload": {},
                    "raw_path": None,
                    "cantidad": 0,
                    "success": False,
                    "error": str(exc),
                    "fecha_extraccion": timestamp,
                }
            )

        current_date += timedelta(days=1)
        if current_date <= end_dt:
            time.sleep(sleep_seconds)

    return results


def fetch_licitaciones_detail_bulk(
    codes: list[str],
    sleep_seconds: float = 0.5,
    client: MercadoPublicoAPIClient | None = None,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Fetch detailed licitation payloads for unique codes."""

    active_settings = settings or get_settings()
    active_client = client or MercadoPublicoAPIClient(settings=active_settings)
    logger = _get_bulk_logger(active_settings)

    unique_codes = [code for code in dict.fromkeys(code.strip() for code in codes if code and code.strip())]
    results: list[dict[str, Any]] = []

    for index, code in enumerate(unique_codes):
        timestamp = datetime.now()
        try:
            payload = active_client.get_licitacion_by_code(code)
            raw_path = _save_json(payload, active_settings.raw_details_data_dir / f"{_sanitize_code(code)}.json")
            results.append(
                {
                    "code": code,
                    "payload": payload,
                    "raw_path": raw_path,
                    "success": True,
                    "error": None,
                    "fecha_extraccion": timestamp,
                    "extraction_status": "success",
                }
            )
        except Exception as exc:
            logger.exception("Detail fetch failed for code %s", code)
            results.append(
                {
                    "code": code,
                    "payload": {},
                    "raw_path": None,
                    "success": False,
                    "error": str(exc),
                    "fecha_extraccion": timestamp,
                    "extraction_status": "error",
                }
            )

        if index < len(unique_codes) - 1:
            time.sleep(sleep_seconds)

    return results


def build_summary_dataset_from_range_results(
    range_results: list[dict[str, Any]],
    deduplicate: bool = False,
) -> pd.DataFrame:
    """Build a summary DataFrame from daily range extraction results."""

    frames = [
        normalize_licitaciones_summary(
            result.get("payload", {}),
            fecha_consulta_origen=result.get("date"),
            source_file=result.get("raw_path"),
            extraction_timestamp=result.get("fecha_extraccion"),
        )
        for result in range_results
        if result.get("success")
    ]

    if not frames:
        return normalize_licitaciones_summary({})

    summary_df = frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)
    if deduplicate and not summary_df.empty:
        summary_df = summary_df.drop_duplicates(subset=["codigo_externo"], keep="last")
    return summary_df


def _count_summary_records(payload: dict[str, Any]) -> int:
    summary_df = normalize_licitaciones_summary(payload)
    return len(summary_df)


def _save_json(payload: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return output_path


def _sanitize_code(code: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in code)


def _get_bulk_logger(settings: Settings) -> logging.Logger:
    logger = logging.getLogger("app.services.extract_bulk")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(settings.logs_data_dir / "bulk_errors.log", encoding="utf-8")
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
