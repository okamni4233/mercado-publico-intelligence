from __future__ import annotations

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app.dashboard.data import (
    ROOT,
    SAMPLE_PATH,
    add_competition,
    amounts_in_clp,
    load_competition,
    load_dataset,
    load_monthly_summary,
    summarize_amounts,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region_unidad": ["Norte", "Norte", "Sur", "Sur", "Sur"],
            "moneda": ["CLP", "CLP", "CLP", "USD", "CLP"],
            "monto_estimado": [10_000_000, 30_000_000, 60_000_000, 5_000, 1],
        }
    )


def test_amounts_in_clp_drops_other_currencies_and_placeholder_amounts() -> None:
    usable = amounts_in_clp(_frame())

    assert usable["monto_mm"].tolist() == [10.0, 30.0, 60.0]


def test_summarize_amounts_reports_count_total_share_and_median() -> None:
    summary = summarize_amounts(_frame(), "region_unidad")

    assert summary.index.tolist() == ["Sur", "Norte"]
    assert summary.loc["Norte", "licitaciones"] == 2
    assert summary.loc["Norte", "monto_total_mm"] == 40.0
    assert summary.loc["Norte", "mediana_mm"] == 20.0
    assert summary["pct_monto"].sum() == pytest.approx(100.0)


def test_summarize_amounts_without_usable_amounts_is_empty() -> None:
    frame = _frame().assign(moneda="USD")

    assert summarize_amounts(frame, "region_unidad").empty


def test_public_sample_loads_with_the_columns_the_dashboard_needs() -> None:
    frame = load_dataset(SAMPLE_PATH)

    assert len(frame) == 1407
    assert frame["codigo_externo"].is_unique
    assert pd.api.types.is_datetime64_any_dtype(frame["fecha_cierre"])
    for column in ("nombre", "estado", "region_unidad", "organismo_nombre", "rubro_principal", "monto_estimado"):
        assert column in frame.columns


def test_monthly_summary_covers_twelve_months() -> None:
    monthly = load_monthly_summary()

    assert monthly["mes"].tolist()[0] == "2025-04"
    assert monthly["mes"].tolist()[-1] == "2026-03"
    assert len(monthly) == 12
    assert monthly["licitaciones"].sum() == 100124


def test_competition_is_attached_by_category_ignoring_case_and_accents() -> None:
    frame = pd.DataFrame({"rubro_principal": ["Servicios de construcción y mantenimiento", "Rubro que no existe", None]})

    result = add_competition(frame, load_competition())

    assert result.loc[0, "oferentes_tipicos_rubro"] == 3
    assert result.loc[0, "pct_poca_competencia_rubro"] == pytest.approx(40.3)
    assert result["oferentes_tipicos_rubro"].isna().tolist() == [False, True, True]


def test_most_sample_licitations_get_the_competition_of_their_category() -> None:
    sample = add_competition(load_dataset(SAMPLE_PATH), load_competition())

    assert sample["oferentes_tipicos_rubro"].notna().mean() > 0.9


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    # Always exercise the public sample, even if a local extraction exists.
    monkeypatch.setattr("app.dashboard.data.LOCAL_PATH", SAMPLE_PATH.with_name("no-existe.csv"))
    return AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=60).run()


def _metric(app: AppTest, label: str) -> str:
    return next(metric.value for metric in app.metric if metric.label == label)


def test_dashboard_renders_the_public_sample_without_errors(app: AppTest) -> None:
    assert not app.exception
    assert _metric(app, "Licitaciones") == "1.407"
    assert _metric(app, "Prioridad alta") == "26"
    assert [tab.label for tab in app.tabs] == ["Resumen", "Montos", "Oportunidades", "Tendencias", "Acerca del puntaje"]


def test_dashboard_region_filter_narrows_the_data(app: AppTest) -> None:
    app.multiselect(key="regiones").set_value(["Región de Antofagasta"]).run()

    assert not app.exception
    assert _metric(app, "Licitaciones") == "40"


def test_dashboard_scoring_profile_can_be_changed(app: AppTest) -> None:
    app.text_area(key="keywords").set_value("medicamento, insumo").run()

    assert not app.exception
    assert _metric(app, "Prioridad alta") != "26"


def test_dashboard_warns_when_no_licitation_matches(app: AppTest) -> None:
    app.text_input(key="texto").set_value("texto que no existe en ninguna licitación").run()

    assert not app.exception
    assert len(app.warning) == 1
    assert len(app.metric) == 0


def test_dashboard_target_categories_raise_priorities(app: AppTest) -> None:
    app.multiselect(key="target_categories").set_value(["Servicios de construcción y mantenimiento"]).run()

    assert not app.exception
    assert int(_metric(app, "Prioridad alta")) > 26
