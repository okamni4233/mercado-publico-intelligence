"""Resume los detalles de licitaciones descargados y genera el grafico del README.

Lee los JSON de data/raw/details/ (ver la seccion "Datos" del README para
regenerarlos), imprime un resumen y guarda assets/licitaciones_por_region.png.

Uso:
    python scripts/resumen_datos.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.transform import normalize_licitacion_detail  # noqa: E402

DETAILS_DIR = ROOT / "data" / "raw" / "details"
OUTPUT = ROOT / "assets" / "licitaciones_por_region.png"


def load_details() -> pd.DataFrame:
    frames = [
        normalize_licitacion_detail(json.loads(path.read_text(encoding="utf-8")), code_override=path.stem)
        for path in sorted(DETAILS_DIR.glob("*.json"))
    ]
    frames = [frame.dropna(axis=1, how="all") for frame in frames if not frame.empty]
    return pd.concat(frames, ignore_index=True).drop_duplicates("codigo_externo")


def short_region(name: str) -> str:
    short = re.sub(r"^Región (del |de )?", "", name).strip()
    return short[:1].upper() + short[1:]


def main() -> int:
    if not any(DETAILS_DIR.glob("*.json")):
        print(f"No hay archivos en {DETAILS_DIR}. Revisa la seccion 'Datos' del README.", file=sys.stderr)
        return 1

    df = load_details()
    publicacion = pd.to_datetime(df["fecha_publicacion"])
    por_region = df["region_unidad"].dropna().map(short_region).value_counts()

    print(f"Licitaciones: {len(df)}")
    print(f"Organismos compradores: {df['organismo_nombre'].nunique()}")
    print(f"Regiones: {df['region_unidad'].nunique()}")
    print(f"Publicadas entre {publicacion.min():%Y-%m-%d} y {publicacion.max():%Y-%m-%d}")
    print(f"Con monto estimado informado: {df['monto_estimado'].notna().sum()} ({df['monto_estimado'].notna().mean():.1%})")
    print(f"Region con mas licitaciones: {por_region.index[0]} ({por_region.iloc[0]}, {por_region.iloc[0] / len(df):.1%})")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    por_region.sort_values().plot(kind="barh", ax=ax, color="#1f77b4")
    ax.set_title(f"Licitaciones por region del organismo comprador (n = {len(df)})")
    ax.set_xlabel("Numero de licitaciones")
    ax.set_ylabel("")
    fig.tight_layout()
    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=150)
    print(f"Grafico guardado en {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
