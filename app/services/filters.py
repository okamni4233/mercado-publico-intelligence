"""Filters over normalized licitation DataFrames."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from app.services.keywords import normalize_text


def filter_licitaciones(
    df: pd.DataFrame,
    regiones: Iterable[str] | None = None,
    estados: Iterable[str] | None = None,
    tipos: Iterable[str] | None = None,
    rubros: Iterable[str] | None = None,
    monto_minimo: float | None = None,
    monto_maximo: float | None = None,
    texto: str | None = None,
) -> pd.DataFrame:
    """Return the rows that satisfy every filter that was given.

    A filter left as ``None`` (or as an empty list or blank text) is ignored.
    Amount filters drop licitations without an informed amount, because there
    is nothing to compare. ``texto`` is searched in the name and description,
    ignoring case and accents.
    """

    mask = pd.Series(True, index=df.index)

    for column, values in (
        ("region_unidad", regiones),
        ("estado", estados),
        ("tipo", tipos),
        ("rubro_principal", rubros),
    ):
        selected = list(values) if values is not None else []
        if selected and column in df.columns:
            mask &= df[column].isin(selected)

    if (monto_minimo is not None or monto_maximo is not None) and "monto_estimado" in df.columns:
        monto = pd.to_numeric(df["monto_estimado"], errors="coerce")
        if monto_minimo is not None:
            mask &= monto.ge(monto_minimo)
        if monto_maximo is not None:
            mask &= monto.le(monto_maximo)

    if texto and texto.strip():
        needle = normalize_text(texto).strip()
        empty = pd.Series("", index=df.index)
        haystack = (
            df.get("nombre", empty).fillna("").astype(str) + " " + df.get("descripcion", empty).fillna("").astype(str)
        ).map(normalize_text)
        mask &= haystack.str.contains(needle, regex=False)

    return df[mask]
