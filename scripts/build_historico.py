"""Descarga los archivos mensuales de datos abiertos de ChileCompra y los resume por licitacion.

No necesita ticket de la API: los archivos son publicos.

Uso:
    python scripts/build_historico.py --desde 2025-04 --hasta 2026-03

Deja:
    data/historico/licitaciones.csv.gz     una fila por licitacion
    data/historico/resumen_mensual.csv     totales por mes de publicacion
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.historico import (  # noqa: E402
    BULK_URL,
    aggregate_tenders,
    monthly_summary,
    read_offer_rows,
)

OUTPUT_DIR = ROOT / "data" / "historico"


def months_between(start: str, end: str) -> list[pd.Period]:
    return list(pd.period_range(start=start, end=end, freq="M"))


def load_month(period: pd.Period) -> tuple[pd.DataFrame, dict[str, int]]:
    url = BULK_URL.format(year=period.year, month=period.month)
    with urllib.request.urlopen(url, timeout=300) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    with archive.open(archive.namelist()[0]) as csv_file:
        rows, stats = read_offer_rows(csv_file)
    return aggregate_tenders(rows), stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--desde", required=True, help="Primer mes, en formato AAAA-MM.")
    parser.add_argument("--hasta", required=True, help="Ultimo mes, en formato AAAA-MM.")
    args = parser.parse_args()

    frames = []
    for period in months_between(args.desde, args.hasta):
        tenders, stats = load_month(period)
        share = stats["filas_validas"] / stats["filas_leidas"] if stats["filas_leidas"] else 0
        print(
            f"{period}: {len(tenders):>6} licitaciones | "
            f"{stats['filas_validas']:>7} de {stats['filas_leidas']:>7} filas validas ({share:.2%})"
        )
        frames.append(tenders)

    history = pd.concat(frames, ignore_index=True).drop_duplicates("codigo_externo", keep="last")
    history = history.sort_values(["fecha_publicacion", "codigo_externo"]).reset_index(drop=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    history.to_csv(OUTPUT_DIR / "licitaciones.csv.gz", index=False, encoding="utf-8", compression="gzip")
    monthly_summary(history).round(2).to_csv(OUTPUT_DIR / "resumen_mensual.csv", index=False, encoding="utf-8")

    print(f"Total: {len(history)} licitaciones en {OUTPUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
