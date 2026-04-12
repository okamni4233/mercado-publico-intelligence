"""Persistence helpers for processed analytical datasets."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from app.config import Settings, get_settings


def save_processed_dataframe(
    dataframe: pd.DataFrame,
    dataset_name: str,
    settings: Settings | None = None,
    timestamp: datetime | None = None,
) -> Path:
    """Save a processed DataFrame into the configured `data/processed` directory."""

    active_settings = settings or get_settings()
    active_timestamp = timestamp or datetime.now()
    safe_name = _sanitize_filename_part(dataset_name)
    filename = f"{safe_name}_{active_timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
    output_path = active_settings.processed_data_dir / filename

    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def _sanitize_filename_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value).strip("_")
