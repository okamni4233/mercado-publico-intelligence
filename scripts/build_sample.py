"""Genera la muestra publica de licitaciones a partir de los detalles descargados.

Lee data/raw/details/*.json y escribe data/sample/licitaciones_muestra.csv,
sin datos personales (ver app/services/sample.py).

Uso:
    python scripts/build_sample.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.sample import build_public_sample  # noqa: E402

DETAILS_DIR = ROOT / "data" / "raw" / "details"
OUTPUT = ROOT / "data" / "sample" / "licitaciones_muestra.csv"


def main() -> int:
    sample = build_public_sample(DETAILS_DIR)
    if sample.empty:
        print(f"No hay archivos en {DETAILS_DIR}. Revisa la seccion 'Dataset' del README.", file=sys.stderr)
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUTPUT, index=False, encoding="utf-8")
    print(f"{len(sample)} licitaciones guardadas en {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
