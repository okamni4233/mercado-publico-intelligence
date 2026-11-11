"""Data loading and aggregation helpers for the dashboard.

Kept free of Streamlit calls so the logic can be tested on its own.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = ROOT / "data" / "sample" / "licitaciones_muestra.csv"
LOCAL_PATH = ROOT / "data" / "processed" / "licitaciones_detalladas.csv"

DATE_COLUMNS = ["fecha_publicacion", "fecha_cierre"]
MIN_VALID_AMOUNT = 1000
# Day the public sample was downloaded; used as the default scoring reference date for it.
SAMPLE_REFERENCE_DATE = date(2026, 4, 6)
MILLION = 1_000_000


def resolve_dataset() -> tuple[Path, str, date]:
    """Pick the dataset to show: a local extraction if there is one, else the public sample.

    Returns the path, a label for the user and the default scoring reference date.
    """

    if LOCAL_PATH.exists():
        return LOCAL_PATH, "Extracción local (data/processed/licitaciones_detalladas.csv)", date.today()
    return (
        SAMPLE_PATH,
        "Muestra pública: 1.407 licitaciones descargadas el 5 y 6 de abril de 2026",
        SAMPLE_REFERENCE_DATE,
    )


def load_dataset(path: Path) -> pd.DataFrame:
    """Load a licitations CSV and make sure the columns the dashboard needs exist."""

    frame = pd.read_csv(path, encoding="utf-8-sig")
    for column in DATE_COLUMNS:
        frame[column] = pd.to_datetime(frame.get(column), errors="coerce")
    for column in ("descripcion", "rubro_principal", "estado", "tipo", "region_unidad", "organismo_nombre", "moneda"):
        if column not in frame.columns:
            frame[column] = pd.NA
    frame["monto_estimado"] = pd.to_numeric(frame.get("monto_estimado"), errors="coerce")
    return frame


def amounts_in_clp(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep licitations with a usable amount in Chilean pesos and add it in millions.

    Other currencies are left out so that amounts can be added up, and amounts
    under $1.000 are dropped because they are placeholders, not estimates.
    """

    usable = frame[(frame["moneda"] == "CLP") & frame["monto_estimado"].ge(MIN_VALID_AMOUNT)].copy()
    usable["monto_mm"] = usable["monto_estimado"] / MILLION
    return usable


def summarize_amounts(frame: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Count, total, share and median of the amount (in millions of pesos) per group."""

    usable = amounts_in_clp(frame).dropna(subset=[group_column])
    columns = ["licitaciones", "monto_total_mm", "pct_monto", "mediana_mm"]
    if usable.empty:
        return pd.DataFrame(columns=columns).rename_axis(group_column)

    grouped = usable.groupby(group_column)["monto_mm"]
    table = pd.DataFrame(
        {
            "licitaciones": grouped.size(),
            "monto_total_mm": grouped.sum(),
            "pct_monto": grouped.sum() / usable["monto_mm"].sum() * 100,
            "mediana_mm": grouped.median(),
        }
    )
    return table.sort_values("monto_total_mm", ascending=False)
