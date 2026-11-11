"""Build a small public sample of licitations without personal data.

The raw API responses include names, job titles, e-mails and phone numbers of
the public officials in charge of each tender, so they are not versioned. The
sample keeps only the fields needed for analysis and for the dashboard, and
redacts contact details that sometimes appear inside the free-text description.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from app.services.transform import (
    normalize_licitacion_detail,
    normalize_licitacion_items,
)

SAMPLE_COLUMNS = [
    "codigo_externo",
    "nombre",
    "codigo_estado",
    "estado",
    "tipo",
    "fecha_publicacion",
    "fecha_cierre",
    "organismo_nombre",
    "comuna_unidad",
    "region_unidad",
    "moneda",
    "monto_estimado",
    "rubro_principal",
    "cantidad_items",
]

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")
# Chilean numbers: optional +56, then a mobile (9 XXXX XXXX) or an area code plus 7 digits.
_PHONE = re.compile(r"(?<![\w.,-])(?:\+?56[\s-]?)?(?:9[\s-]?\d{4}[\s-]?\d{4}|\d{2}[\s-]?\d{7})(?![\w-])")


def redact_contact_details(text: str | None) -> str | None:
    """Replace e-mails, RUTs and phone numbers found in free text."""

    if text is None or pd.isna(text):
        return None
    redacted = _EMAIL.sub("[correo]", str(text))
    redacted = _RUT.sub("[rut]", redacted)
    redacted = _PHONE.sub("[telefono]", redacted)
    return redacted


def main_category(items: pd.DataFrame) -> pd.DataFrame:
    """Return, per licitation, its most frequent top-level item category and its item count.

    Item categories come as a path ("Level 1 / Level 2 / Level 3"); the first
    level is used as the licitation's main category ("rubro").
    """

    if items.empty:
        return pd.DataFrame(columns=["codigo_externo", "rubro_principal", "cantidad_items"])

    frame = items[["codigo_externo", "categoria"]].copy()
    frame["rubro"] = frame["categoria"].astype("string").str.split("/").str[0].str.strip()

    counts = frame.groupby("codigo_externo").size().rename("cantidad_items")
    rubro = (
        frame.dropna(subset=["rubro"])
        .groupby("codigo_externo")["rubro"]
        .agg(lambda values: values.value_counts().index[0])
        .rename("rubro_principal")
    )
    return pd.concat([rubro, counts], axis=1).reset_index()


def build_public_sample(details_dir: str | Path) -> pd.DataFrame:
    """Build the public sample from the raw detail JSON files in ``details_dir``."""

    details: list[pd.DataFrame] = []
    items: list[pd.DataFrame] = []
    for path in sorted(Path(details_dir).glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        detail = normalize_licitacion_detail(payload, code_override=path.stem).dropna(axis=1, how="all")
        if not detail.empty:
            details.append(detail)
        item_frame = normalize_licitacion_items(payload).dropna(axis=1, how="all")
        if not item_frame.empty:
            items.append(item_frame)

    if not details:
        return pd.DataFrame(columns=SAMPLE_COLUMNS)

    frame = pd.concat(details, ignore_index=True).drop_duplicates("codigo_externo")
    categories = main_category(pd.concat(items, ignore_index=True) if items else pd.DataFrame())
    frame = frame.merge(categories, on="codigo_externo", how="left")

    frame["nombre"] = frame["nombre"].map(redact_contact_details)
    frame["cantidad_items"] = frame["cantidad_items"].fillna(0).astype(int)

    return frame.reindex(columns=SAMPLE_COLUMNS).sort_values("codigo_externo").reset_index(drop=True)
