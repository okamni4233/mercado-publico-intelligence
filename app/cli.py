"""Command-line interface for Mercado Publico Intelligence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer

from app.api.client import MercadoPublicoAPIClient
from app.config import get_settings
from app.logging_config import configure_logging
from app.services.build_dataset import build_bulk_dataset
from app.services.build_dataset import (
    export_analysis_ready as export_analysis_ready_files,
)
from app.services.extract import (
    fetch_licitaciones_by_date,
    fetch_licitaciones_today,
    save_raw_payload,
)
from app.services.extract_bulk import fetch_licitaciones_range
from app.services.load import save_processed_dataframe
from app.services.scoring import load_scoring_config, score_licitaciones
from app.services.transform import normalize_items, normalize_licitaciones

cli = typer.Typer(add_completion=False, help="CLI para Mercado Publico Intelligence.")


@cli.callback()
def main() -> None:
    """Initialize CLI configuration."""

    settings = get_settings()
    configure_logging(settings.log_level)


@cli.command("fetch-today")
def fetch_today(
    estado: str | None = typer.Option(default=None, help="Estado opcional de la licitacion."),
) -> None:
    """Fetch licitations for the current day."""

    client = MercadoPublicoAPIClient()
    payload = client.get_licitaciones_today(estado=estado)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@cli.command("fetch-date")
def fetch_date(
    date: str = typer.Option(..., "--date", help="Fecha en formato YYYY-MM-DD o ddmmaaaa."),
    estado: str | None = typer.Option(default=None, help="Estado opcional de la licitacion."),
) -> None:
    """Fetch licitations for a specific date."""

    client = MercadoPublicoAPIClient()
    payload = client.get_licitaciones_by_date(target_date=date, estado=estado)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@cli.command("fetch-code")
def fetch_code(code: str = typer.Option(..., "--code", help="Codigo externo de la licitacion.")) -> None:
    """Fetch a licitation by code."""

    client = MercadoPublicoAPIClient()
    payload = client.get_licitacion_by_code(codigo=code)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@cli.command("fetch-range")
def fetch_range(
    start_date: str = typer.Option(..., "--start-date", help="Fecha inicial en formato YYYY-MM-DD."),
    end_date: str = typer.Option(..., "--end-date", help="Fecha final en formato YYYY-MM-DD."),
    sleep_seconds: float = typer.Option(0.5, "--sleep-seconds", help="Pausa entre requests."),
    estado: str | None = typer.Option(default=None, help="Estado opcional para filtrar la consulta."),
) -> None:
    """Fetch licitations day by day for a date range and save raw files."""

    results = fetch_licitaciones_range(
        start_date=start_date,
        end_date=end_date,
        sleep_seconds=sleep_seconds,
        estado=estado,
    )

    for result in results:
        if result.get("success"):
            typer.echo(
                f"{result['date']} | licitaciones={result['cantidad']} | archivo={result['raw_path']}"
            )
        else:
            typer.echo(f"{result['date']} | ERROR | {result['error']}")


@cli.command("build-dataset")
def build_dataset(
    date: str = typer.Option(..., "--date", help="Fecha objetivo en formato YYYY-MM-DD o ddmmaaaa."),
    estado: str | None = typer.Option(default=None, help="Estado opcional para filtrar la consulta."),
) -> None:
    """Build a processed dataset from licitations returned by the API."""

    payload = fetch_licitaciones_by_date(target_date=date, estado=estado)
    licitaciones_df = normalize_licitaciones(payload)
    items_df = normalize_items(payload)

    raw_path = save_raw_payload(payload, prefix=f"licitaciones_raw_{date}")
    licitaciones_path = save_processed_dataframe(licitaciones_df, dataset_name=f"licitaciones_{date}")
    items_path = save_processed_dataframe(items_df, dataset_name=f"licitaciones_items_{date}")

    typer.echo("Dataset generado correctamente.")
    typer.echo(f"JSON crudo: {raw_path}")
    typer.echo(f"CSV licitaciones: {licitaciones_path}")
    typer.echo(f"CSV items: {items_path}")
    typer.echo(f"Filas licitaciones: {len(licitaciones_df)}")
    typer.echo(f"Filas items: {len(items_df)}")


@cli.command("build-dataset-today")
def build_dataset_today(
    estado: str | None = typer.Option(default=None, help="Estado opcional para filtrar la consulta."),
) -> None:
    """Build a processed dataset for licitations returned today."""

    payload = fetch_licitaciones_today(estado=estado)
    licitaciones_df = normalize_licitaciones(payload)
    items_df = normalize_items(payload)

    raw_path = save_raw_payload(payload, prefix="licitaciones_raw_today")
    licitaciones_path = save_processed_dataframe(licitaciones_df, dataset_name="licitaciones_today")
    items_path = save_processed_dataframe(items_df, dataset_name="licitaciones_items_today")

    typer.echo("Dataset diario generado correctamente.")
    typer.echo(f"JSON crudo: {raw_path}")
    typer.echo(f"CSV licitaciones: {licitaciones_path}")
    typer.echo(f"CSV items: {items_path}")
    typer.echo(f"Filas licitaciones: {len(licitaciones_df)}")
    typer.echo(f"Filas items: {len(items_df)}")


@cli.command("build-bulk-dataset")
def build_bulk_dataset_command(
    start_date: str = typer.Option(..., "--start-date", help="Fecha inicial en formato YYYY-MM-DD."),
    end_date: str = typer.Option(..., "--end-date", help="Fecha final en formato YYYY-MM-DD."),
    sleep_seconds: float = typer.Option(0.2, "--sleep-seconds", help="Pausa entre requests."),
    estado: str | None = typer.Option(default=None, help="Estado opcional para filtrar la consulta."),
    deduplicate_summary: bool = typer.Option(False, "--deduplicate-summary", help="Deduplicar resumen por codigo."),
    limit: int | None = typer.Option(None, "--limit", help="Procesar solo los primeros N codigos unicos."),
    skip_existing_details: bool = typer.Option(
        False,
        "--skip-existing-details",
        help="Reutilizar detalles ya guardados en data/raw/details.",
    ),
) -> None:
    """Build summary, detailed and item datasets for a date range."""

    result = build_bulk_dataset(
        start_date=start_date,
        end_date=end_date,
        sleep_seconds=sleep_seconds,
        estado=estado,
        deduplicate_summary=deduplicate_summary,
        limit=limit,
        skip_existing_details=skip_existing_details,
    )

    typer.echo("Bulk dataset generado correctamente.")
    typer.echo(f"Dias consultados: {result['dias_consultados']}")
    typer.echo(f"Licitaciones resumidas: {result['licitaciones_resumidas']}")
    typer.echo(f"Codigos unicos: {result['codigos_unicos']}")
    typer.echo(f"Detalles exitosos: {result['detalles_exitosos']}")
    typer.echo(f"Errores: {result['errores']}")
    typer.echo(f"Resumen CSV: {result['summary_path']}")
    typer.echo(f"Detalle CSV: {result['details_path']}")
    typer.echo(f"Items CSV: {result['items_path']}")
    typer.echo(f"Detalle parcial CSV: {result['partial_details_path']}")
    typer.echo(f"Items parcial CSV: {result['partial_items_path']}")
    if result["interrupted"]:
        typer.echo("Proceso interrumpido. Se guardaron resultados parciales y finales con lo procesado.")


@cli.command("export-analysis-ready")
def export_analysis_ready_command(
    start_date: str = typer.Option(..., "--start-date", help="Fecha inicial de referencia."),
    end_date: str = typer.Option(..., "--end-date", help="Fecha final de referencia."),
    use_partials: bool = typer.Option(
        False,
        "--use-partials",
        help="Usar archivos parciales si los finales no existen o si quieres exportar avance.",
    ),
) -> None:
    """Export processed datasets into analysis-ready CSV files."""

    try:
        result = export_analysis_ready_files(use_partials=use_partials)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    typer.echo(f"Rango de referencia: {start_date} a {end_date}")
    typer.echo(f"Licitaciones analysis-ready: {result['licitaciones_analysis_ready']}")
    typer.echo(f"Items analysis-ready: {result['items_analysis_ready']}")


@cli.command("score-dataset")
def score_dataset(
    input_path: Path | None = typer.Option(
        None,
        "--input",
        help="Ruta al CSV de licitaciones detalladas. Por defecto usa data/processed/licitaciones_detalladas.csv.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        help="Ruta de salida del CSV scoreado. Por defecto usa data/processed/licitaciones_scored.csv.",
    ),
    config_path: Path | None = typer.Option(
        None,
        "--config",
        help="JSON con el perfil de scoring (ver config/scoring.example.json). Por defecto usa el perfil de ejemplo.",
    ),
    reference_date: str | None = typer.Option(
        None,
        "--reference-date",
        help="Fecha YYYY-MM-DD contra la que se decide si una licitacion sigue abierta. Por defecto, hoy.",
    ),
) -> None:
    """Score a detailed licitations dataset and export the result to CSV."""

    settings = get_settings()
    resolved_input = input_path or (settings.processed_data_dir / "licitaciones_detalladas.csv")
    resolved_output = output_path or (settings.processed_data_dir / "licitaciones_scored.csv")

    if not resolved_input.exists():
        typer.echo(f"No existe el archivo de entrada: {resolved_input}")
        raise typer.Exit(code=1)

    dataframe = pd.read_csv(resolved_input, encoding="utf-8-sig")
    config = load_scoring_config(config_path) if config_path else None
    scored_df = score_licitaciones(dataframe, config=config, reference_date=reference_date)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    scored_df.to_csv(resolved_output, index=False, encoding="utf-8-sig")

    typer.echo("Dataset scoreado correctamente.")
    typer.echo(f"Input: {resolved_input}")
    typer.echo(f"Output: {resolved_output}")
    typer.echo(f"Filas procesadas: {len(scored_df)}")


@cli.command("run-dashboard")
def run_dashboard() -> None:
    """Guide the user to run the Streamlit application."""

    typer.echo("Ejecuta: streamlit run streamlit_app.py")


if __name__ == "__main__":
    cli()
