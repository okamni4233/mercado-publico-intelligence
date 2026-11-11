"""Tender-level history built from ChileCompra's open-data monthly files.

ChileCompra publishes one CSV per month with every tender published that month
(https://datos-abiertos.chilecompra.cl). Each row is one offer for one item of
one tender, so a tender appears in as many rows as offers it received. Tenders
that received no offers do not appear at all.

This module reduces a monthly file to one row per tender, keeping only
non-personal fields plus the outcome: final state, number of bidders and number
of awarded suppliers. Supplier identities are not kept.
"""

from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd

BULK_URL = "https://transparenciachc.blob.core.windows.net/lic-da/{year}-{month}.zip"

RAW_COLUMNS = [
    "CodigoExterno",
    "Nombre",
    "CodigoEstado",
    "Estado",
    "Tipo",
    "FechaPublicacion",
    "FechaCierre",
    "NombreOrganismo",
    "sector",
    "RegionUnidad",
    "CodigoMoneda",
    "MontoEstimado",
    "NumeroOferentes",
    "Codigoitem",
    "Rubro1",
    "CodigoProveedor",
    "Oferta seleccionada",
]

TENDER_COLUMNS = [
    "codigo_externo",
    "nombre",
    "codigo_estado",
    "estado",
    "tipo",
    "fecha_publicacion",
    "fecha_cierre",
    "organismo_nombre",
    "sector",
    "region_unidad",
    "moneda",
    "monto_estimado",
    "rubro_principal",
    "cantidad_items",
    "numero_oferentes",
    "proveedores_adjudicados",
]

AWARDED_STATE_CODE = 8
_CODE_PATTERN = r"^\d+-\d+-[A-Z0-9]+$"
_OFFER_RESULTS = {"Seleccionada", "No Seleccionada"}
_SELECTED = "Seleccionada"


def read_offer_rows(source: str | Path | IO[bytes]) -> tuple[pd.DataFrame, dict[str, int]]:
    """Read a monthly open-data CSV and keep only the rows that parse cleanly.

    A small share of rows is broken at the source (unescaped quotes and line
    breaks inside free-text fields shift the columns). A row is kept only if
    its tender code, state code and offer result look valid. Returns the valid
    rows and counts of what was read and kept.
    """

    raw = pd.read_csv(
        source,
        sep=";",
        encoding="latin-1",
        dtype=str,
        usecols=RAW_COLUMNS,
        on_bad_lines="skip",
    )
    valid = (
        raw["CodigoExterno"].str.match(_CODE_PATTERN, na=False)
        & raw["CodigoEstado"].str.fullmatch(r"\d+", na=False)
        & raw["Oferta seleccionada"].isin(_OFFER_RESULTS)
        & pd.to_datetime(raw["FechaPublicacion"], format="%Y-%m-%d", errors="coerce").notna()
    )
    rows = raw[valid].copy()
    stats = {"filas_leidas": len(raw), "filas_validas": len(rows)}
    return rows, stats


def aggregate_tenders(rows: pd.DataFrame) -> pd.DataFrame:
    """Reduce offer rows to one row per tender."""

    if rows.empty:
        return pd.DataFrame(columns=TENDER_COLUMNS)

    grouped = rows.groupby("CodigoExterno", sort=True)
    first = grouped.first()

    selected = rows[rows["Oferta seleccionada"] == _SELECTED]
    awarded_suppliers = selected.groupby("CodigoExterno")["CodigoProveedor"].nunique()
    main_category = (
        rows.dropna(subset=["Rubro1"])
        .assign(Rubro1=lambda frame: frame["Rubro1"].str.strip())
        .groupby("CodigoExterno")["Rubro1"]
        .agg(lambda values: values.value_counts().index[0])
    )

    tenders = pd.DataFrame(
        {
            "nombre": first["Nombre"].str.strip(),
            "codigo_estado": pd.to_numeric(first["CodigoEstado"], errors="coerce").astype("Int64"),
            "estado": first["Estado"].str.strip(),
            "tipo": first["Tipo"].str.strip(),
            "fecha_publicacion": pd.to_datetime(first["FechaPublicacion"], format="%Y-%m-%d", errors="coerce"),
            "fecha_cierre": pd.to_datetime(first["FechaCierre"], format="%Y-%m-%d", errors="coerce"),
            "organismo_nombre": first["NombreOrganismo"].str.strip(),
            "sector": first["sector"].str.strip(),
            "region_unidad": first["RegionUnidad"].str.strip(),
            "moneda": first["CodigoMoneda"].str.strip(),
            "monto_estimado": _to_number(first["MontoEstimado"]),
            "rubro_principal": main_category,
            "cantidad_items": grouped["Codigoitem"].nunique(),
            "numero_oferentes": _to_number(first["NumeroOferentes"]).astype("Int64"),
            "proveedores_adjudicados": awarded_suppliers,
        }
    )
    tenders["proveedores_adjudicados"] = tenders["proveedores_adjudicados"].fillna(0).astype(int)
    tenders = tenders.rename_axis("codigo_externo").reset_index()
    return tenders.reindex(columns=TENDER_COLUMNS)


def monthly_summary(tenders: pd.DataFrame, min_amount: float = 1000) -> pd.DataFrame:
    """Per publication month: tenders, share awarded, bidders and estimated amounts in CLP."""

    frame = tenders.dropna(subset=["fecha_publicacion"]).copy()
    frame["mes"] = frame["fecha_publicacion"].dt.to_period("M").astype(str)
    frame["adjudicada"] = frame["codigo_estado"].eq(AWARDED_STATE_CODE)
    amount = frame["monto_estimado"].where((frame["moneda"] == "CLP") & frame["monto_estimado"].ge(min_amount))
    frame["monto_clp_mm"] = amount / 1_000_000

    grouped = frame.groupby("mes")
    summary = pd.DataFrame(
        {
            "licitaciones": grouped.size(),
            "pct_adjudicadas": grouped["adjudicada"].mean() * 100,
            "mediana_oferentes": grouped["numero_oferentes"].median(),
            "con_monto_clp": grouped["monto_clp_mm"].count(),
            "monto_total_mm": grouped["monto_clp_mm"].sum(),
            "mediana_monto_mm": grouped["monto_clp_mm"].median(),
        }
    )
    return summary.reset_index()


def _to_number(series: pd.Series) -> pd.Series:
    """Parse numbers written with a decimal comma or point; anything else becomes missing."""

    return pd.to_numeric(series.str.strip().str.replace(",", ".", regex=False), errors="coerce")
