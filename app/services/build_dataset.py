"""Dataset builders for bulk Mercado Publico extractions."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.api.client import MercadoPublicoAPIClient
from app.config import Settings, get_settings
from app.services.extract_bulk import (
    build_summary_dataset_from_range_results,
    fetch_licitaciones_range,
)
from app.services.transform import (
    build_analysis_ready_items,
    build_analysis_ready_licitaciones,
    normalize_detail_records,
)

logger = logging.getLogger(__name__)


def build_bulk_dataset(
    start_date: str,
    end_date: str,
    sleep_seconds: float = 0.2,
    deduplicate_summary: bool = False,
    estado: str | None = None,
    settings: Settings | None = None,
    limit: int | None = None,
    skip_existing_details: bool = False,
) -> dict[str, Any]:
    """Run the bulk extraction and build processed CSV datasets."""

    active_settings = settings or get_settings()
    client = MercadoPublicoAPIClient(settings=active_settings)
    logger.info("Starting bulk dataset build for range %s to %s", start_date, end_date)

    range_results = fetch_licitaciones_range(
        start_date=start_date,
        end_date=end_date,
        sleep_seconds=sleep_seconds,
        estado=estado,
        settings=active_settings,
        client=client,
    )

    summary_df = build_summary_dataset_from_range_results(
        range_results,
        deduplicate=deduplicate_summary,
    )
    summary_path = _save_csv(summary_df, active_settings.processed_data_dir / "licitaciones_resumen.csv")
    logger.info("Summary dataset saved to %s with %s rows", summary_path, len(summary_df))

    unique_codes = (
        summary_df["codigo_externo"].dropna().astype(str).str.strip().loc[lambda series: series.ne("")].unique().tolist()
        if not summary_df.empty
        else []
    )
    if limit is not None and limit > 0:
        unique_codes = unique_codes[:limit]
        logger.info("Applying limit=%s. Codes to process: %s", limit, len(unique_codes))
    else:
        logger.info("Unique codes found: %s", len(unique_codes))

    detail_entries: list[dict[str, Any]] = []
    details_df = pd.DataFrame()
    items_df = pd.DataFrame()
    processed_count = 0
    error_count = sum(1 for result in range_results if not result.get("success"))
    successful_details = 0
    interrupted = False

    try:
        for code in unique_codes:
            processed_count += 1
            detail_path = active_settings.raw_details_data_dir / f"{_sanitize_code(code)}.json"
            request_made = False

            try:
                if skip_existing_details and detail_path.exists():
                    try:
                        logger.info("Reusing existing detail for code %s from %s", code, detail_path)
                        payload = _load_json(detail_path)
                        entry = {
                            "code": code,
                            "payload": payload,
                            "source_file": detail_path,
                            "success": True,
                            "error": None,
                            "fecha_extraccion": datetime.now(),
                            "extraction_status": "success",
                        }
                    except Exception:
                        logger.warning("Existing detail for code %s could not be read. Refetching.", code)
                        request_made = True
                        payload = client.get_licitacion_by_code(code)
                        saved_path = _save_json(payload, detail_path)
                        entry = {
                            "code": code,
                            "payload": payload,
                            "source_file": saved_path,
                            "success": True,
                            "error": None,
                            "fecha_extraccion": datetime.now(),
                            "extraction_status": "success",
                        }
                else:
                    request_made = True
                    payload = client.get_licitacion_by_code(code)
                    saved_path = _save_json(payload, detail_path)
                    entry = {
                        "code": code,
                        "payload": payload,
                        "source_file": saved_path,
                        "success": True,
                        "error": None,
                        "fecha_extraccion": datetime.now(),
                        "extraction_status": "success",
                    }
                successful_details += 1
            except Exception as exc:
                error_count += 1
                logger.exception("Detail fetch failed for code %s", code)
                entry = {
                    "code": code,
                    "payload": {},
                    "source_file": detail_path if detail_path.exists() else None,
                    "success": False,
                    "error": str(exc),
                    "fecha_extraccion": datetime.now(),
                    "extraction_status": "error",
                }

            detail_entries.append(entry)

            if processed_count % 10 == 0 or processed_count == len(unique_codes):
                logger.info(
                    "Detail progress | total=%s | processed=%s | remaining=%s | errors=%s | pct=%.1f%%",
                    len(unique_codes),
                    processed_count,
                    len(unique_codes) - processed_count,
                    error_count,
                    _calculate_percentage(processed_count, len(unique_codes)),
                )

            if processed_count % 25 == 0:
                details_df, items_df = _save_partial_results(detail_entries, active_settings)

            if request_made and processed_count < len(unique_codes):
                time.sleep(sleep_seconds)

    except KeyboardInterrupt:
        interrupted = True
        logger.warning("Bulk dataset build interrupted by user. Saving partial results.")
        details_df, items_df = _save_partial_results(detail_entries, active_settings)

    if detail_entries:
        details_df, items_df = normalize_detail_records(detail_entries)
    else:
        details_df, items_df = normalize_detail_records([])

    details_path = _save_csv(details_df, active_settings.processed_data_dir / "licitaciones_detalladas.csv")
    items_path = _save_csv(items_df, active_settings.processed_data_dir / "licitaciones_items.csv")

    logger.info(
        "Bulk dataset build finished | interrupted=%s | codes=%s | success=%s | errors=%s",
        interrupted,
        len(unique_codes),
        successful_details,
        error_count,
    )

    return {
        "dias_consultados": len(range_results),
        "licitaciones_resumidas": len(summary_df),
        "codigos_unicos": len(unique_codes),
        "detalles_exitosos": successful_details,
        "errores": error_count,
        "summary_path": summary_path,
        "details_path": details_path,
        "items_path": items_path,
        "partial_details_path": active_settings.processed_data_dir / "licitaciones_detalladas_partial.csv",
        "partial_items_path": active_settings.processed_data_dir / "licitaciones_items_partial.csv",
        "range_results": range_results,
        "detail_results": detail_entries,
        "interrupted": interrupted,
    }


def export_analysis_ready(
    settings: Settings | None = None,
    use_partials: bool = False,
) -> dict[str, Path]:
    """Export processed bulk datasets into analysis-ready CSV files."""

    active_settings = settings or get_settings()
    final_details_path = active_settings.processed_data_dir / "licitaciones_detalladas.csv"
    final_items_path = active_settings.processed_data_dir / "licitaciones_items.csv"
    partial_details_path = active_settings.processed_data_dir / "licitaciones_detalladas_partial.csv"
    partial_items_path = active_settings.processed_data_dir / "licitaciones_items_partial.csv"

    if use_partials:
        if partial_details_path.exists() and partial_items_path.exists():
            details_path = partial_details_path
            items_path = partial_items_path
            logger.info("Using partial datasets for analysis-ready export.")
        elif final_details_path.exists() and final_items_path.exists():
            details_path = final_details_path
            items_path = final_items_path
        else:
            raise FileNotFoundError(
                "No partial or final processed datasets were found. Run build-bulk-dataset first."
            )
    else:
        if final_details_path.exists() and final_items_path.exists():
            details_path = final_details_path
            items_path = final_items_path
        elif partial_details_path.exists() and partial_items_path.exists():
            raise FileNotFoundError(
                "Final datasets do not exist yet, but partial datasets were found. "
                "Use --use-partials to export from partial files."
            )
        else:
            raise FileNotFoundError(
                "Processed bulk datasets do not exist yet. Run build-bulk-dataset first."
            )

    details_df = pd.read_csv(details_path, encoding="utf-8-sig")
    items_df = pd.read_csv(items_path, encoding="utf-8-sig")

    analysis_details = build_analysis_ready_licitaciones(details_df)
    analysis_items = build_analysis_ready_items(items_df)

    export_details_path = _save_csv(
        analysis_details,
        active_settings.exports_data_dir / "licitaciones_analysis_ready.csv",
    )
    export_items_path = _save_csv(
        analysis_items,
        active_settings.exports_data_dir / "items_analysis_ready.csv",
    )

    return {
        "licitaciones_analysis_ready": export_details_path,
        "items_analysis_ready": export_items_path,
    }


def _save_partial_results(
    detail_entries: list[dict[str, Any]],
    settings: Settings,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    details_df, items_df = normalize_detail_records(detail_entries)
    partial_details_path = _save_csv(
        details_df,
        settings.processed_data_dir / "licitaciones_detalladas_partial.csv",
    )
    partial_items_path = _save_csv(
        items_df,
        settings.processed_data_dir / "licitaciones_items_partial.csv",
    )
    logger.info(
        "Partial datasets saved | details=%s | items=%s",
        partial_details_path,
        partial_items_path,
    )
    return details_df, items_df


def _save_csv(dataframe: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def _save_json(payload: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return output_path


def _load_json(input_path: Path) -> dict[str, Any]:
    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {input_path}")
    return data


def _sanitize_code(code: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in code)


def _calculate_percentage(processed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (processed / total) * 100
