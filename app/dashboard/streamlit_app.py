"""Streamlit dashboard to explore licitations and their opportunity score."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.data import (
    MILLION,
    add_competition,
    amounts_in_clp,
    load_competition,
    load_dataset,
    load_monthly_summary,
    resolve_dataset,
    summarize_amounts,
)
from app.services.filters import filter_licitaciones
from app.services.scoring import ScoringConfig, score_licitaciones

GROUPS = {
    "Región": "region_unidad",
    "Organismo comprador": "organismo_nombre",
    "Rubro": "rubro_principal",
}
PRIORITIES = ["alta", "media", "baja"]


@st.cache_data
def _load(path: str) -> pd.DataFrame:
    return load_dataset(path)


def _number(value: float, decimals: int = 0) -> str:
    """Format a number with Spanish separators (1.234,5)."""

    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _split_words(text: str) -> list[str]:
    return [word.strip() for word in text.replace("\n", ",").split(",") if word.strip()]


def _options(frame: pd.DataFrame, column: str) -> list[str]:
    return sorted(frame[column].dropna().astype(str).unique())


def _sidebar(frame: pd.DataFrame, source_label: str, default_reference) -> tuple[pd.DataFrame, ScoringConfig, object]:
    st.sidebar.header("Datos")
    st.sidebar.caption(source_label)

    st.sidebar.header("Filtros")
    regiones = st.sidebar.multiselect("Región", _options(frame, "region_unidad"), key="regiones")
    estados = st.sidebar.multiselect("Estado", _options(frame, "estado"), key="estados")
    rubros = st.sidebar.multiselect("Rubro", _options(frame, "rubro_principal"), key="rubros")
    texto = st.sidebar.text_input("Texto en el nombre", key="texto")
    monto_minimo = st.sidebar.number_input(
        "Monto mínimo (millones de $)",
        min_value=0.0,
        value=0.0,
        step=10.0,
        key="monto_minimo",
        help="Si es mayor que 0, se descartan las licitaciones sin monto informado.",
    )

    filtered = filter_licitaciones(
        frame,
        regiones=regiones,
        estados=estados,
        rubros=rubros,
        texto=texto,
        monto_minimo=monto_minimo * MILLION if monto_minimo > 0 else None,
    )

    st.sidebar.header("Perfil del puntaje")
    defaults = ScoringConfig()
    keywords = st.sidebar.text_area(
        "Palabras clave (en singular, separadas por coma)",
        ", ".join(defaults.keywords),
        key="keywords",
    )
    excluded = st.sidebar.text_area(
        "Palabras excluidas",
        ", ".join(defaults.excluded_keywords),
        key="excluded",
    )
    region_options = _options(frame, "region_unidad")
    default_regions = [
        region for region in region_options if any(token in region.lower() for token in ("antofagasta", "tarapacá", "atacama"))
    ]
    priority_regions = st.sidebar.multiselect(
        "Regiones prioritarias", region_options, default=default_regions, key="priority_regions"
    )
    target_categories = st.sidebar.multiselect(
        "Rubros objetivo",
        _options(frame, "rubro_principal"),
        key="target_categories",
        help="Rubro oficial de la licitación. Es una señal de relevancia más confiable que las palabras clave.",
    )
    reference_date = st.sidebar.date_input(
        "Fecha de referencia",
        value=default_reference,
        key="reference_date",
        help="Una licitación suma puntos si su fecha de cierre es posterior a esta fecha.",
    )

    config = ScoringConfig(
        keywords=_split_words(keywords),
        excluded_keywords=_split_words(excluded),
        priority_regions=priority_regions,
        target_categories=target_categories,
    )
    return filtered, config, reference_date


def _kpis(scored: pd.DataFrame) -> None:
    with_amount = amounts_in_clp(scored)
    median = f"${_number(with_amount['monto_mm'].median(), 1)} MM" if not with_amount.empty else "sin datos"
    share = f"{_number(len(with_amount) / len(scored) * 100, 1)} %"

    columns = st.columns(5)
    columns[0].metric("Licitaciones", _number(len(scored)))
    columns[1].metric("Organismos", _number(scored["organismo_nombre"].nunique()))
    columns[2].metric("Con monto en pesos", share)
    columns[3].metric("Monto mediano", median)
    columns[4].metric("Prioridad alta", _number(int((scored["prioridad"] == "alta").sum())))


def _tab_resumen(scored: pd.DataFrame) -> None:
    left, right = st.columns(2)

    by_region = scored["region_unidad"].value_counts().rename_axis("Región").reset_index(name="Licitaciones")
    left.subheader("Licitaciones por región")
    left.plotly_chart(
        px.bar(by_region.sort_values("Licitaciones"), x="Licitaciones", y="Región", orientation="h", height=520),
        use_container_width=True,
    )

    by_state = scored["estado"].value_counts().rename_axis("Estado").reset_index(name="Licitaciones")
    right.subheader("Licitaciones por estado")
    right.plotly_chart(px.bar(by_state, x="Estado", y="Licitaciones", height=520), use_container_width=True)


def _tab_montos(scored: pd.DataFrame) -> None:
    usable = amounts_in_clp(scored)
    st.caption(
        f"{_number(len(usable))} de {_number(len(scored))} licitaciones tienen un monto estimado en pesos utilizable. "
        "Los totales suelen estar dominados por unas pocas licitaciones muy grandes; "
        "la mediana describe mejor a la licitación típica."
    )
    if usable.empty:
        st.info("Ninguna licitación del filtro actual tiene monto en pesos.")
        return

    label = st.radio("Agrupar por", list(GROUPS), horizontal=True, key="grupo")
    summary = summarize_amounts(scored, GROUPS[label]).head(15)

    chart_data = summary.reset_index().rename(
        columns={GROUPS[label]: label, "monto_total_mm": "Monto total (MM$)", "mediana_mm": "Mediana (MM$)"}
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(chart_data.iloc[::-1], x="Monto total (MM$)", y=label, orientation="h", height=520, title="Monto estimado total"),
        use_container_width=True,
    )
    right.plotly_chart(
        px.bar(chart_data.iloc[::-1], x="Mediana (MM$)", y=label, orientation="h", height=520, title="Mediana por licitación"),
        use_container_width=True,
    )

    st.dataframe(
        summary.rename(
            columns={
                "licitaciones": "Licitaciones con monto",
                "monto_total_mm": "Monto total (MM$)",
                "pct_monto": "% del monto",
                "mediana_mm": "Mediana (MM$)",
            }
        ).round(1),
        use_container_width=True,
    )


def _tab_oportunidades(scored: pd.DataFrame) -> None:
    selected = st.multiselect("Prioridad", PRIORITIES, default=["alta", "media"], key="prioridades")
    table = scored[scored["prioridad"].isin(selected)].sort_values(["score", "monto_estimado"], ascending=False)

    st.caption(f"{_number(len(table))} licitaciones con la prioridad seleccionada.")
    columns = [
        "codigo_externo",
        "nombre",
        "organismo_nombre",
        "region_unidad",
        "estado",
        "fecha_cierre",
        "moneda",
        "monto_estimado",
        "oferentes_tipicos_rubro",
        "pct_poca_competencia_rubro",
        "score",
        "prioridad",
    ]
    st.caption(
        "Las dos columnas de competencia vienen del histórico de 12 meses: la mediana de oferentes del rubro "
        "y el porcentaje de sus licitaciones que recibió 2 oferentes o menos. Describen al rubro, no a esta licitación."
    )
    st.dataframe(table[columns], use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar esta tabla (CSV)",
        table[columns].to_csv(index=False).encode("utf-8-sig"),
        file_name="licitaciones_priorizadas.csv",
        mime="text/csv",
    )


def _tab_tendencias() -> None:
    monthly = load_monthly_summary()
    st.caption(
        f"Licitaciones con al menos una oferta publicadas entre {monthly['mes'].iloc[0]} y {monthly['mes'].iloc[-1]} "
        f"({_number(monthly['licitaciones'].sum())} en total), según los datos abiertos de ChileCompra. "
        "No depende de los filtros de la barra lateral."
    )

    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(monthly, x="mes", y="licitaciones", title="Licitaciones publicadas por mes", height=380),
        use_container_width=True,
    )
    right.plotly_chart(
        px.line(monthly, x="mes", y="mediana_monto_mm", markers=True, title="Mediana del monto estimado (MM$)", height=380),
        use_container_width=True,
    )
    st.plotly_chart(
        px.line(monthly, x="mes", y="pct_adjudicadas", markers=True, title="% de licitaciones adjudicadas", height=320),
        use_container_width=True,
    )
    st.info(
        "La baja de la adjudicación en los meses más recientes se debe en buena parte a licitaciones que aún no se "
        "resuelven, no a que se adjudique menos."
    )


def _tab_acerca(config: ScoringConfig, reference_date) -> None:
    st.markdown(
        f"""
**Cómo se calcula el puntaje.** Es una suma de puntos por reglas fijas, de 0 a 100:

| Regla | Puntos |
|---|---|
| El texto contiene una palabra clave | +{config.points_keyword} |
| Contiene dos o más palabras clave distintas | +{config.points_multiple_keywords} |
| La licitación está publicada | +{config.points_published} |
| Cierra después de la fecha de referencia ({reference_date:%d-%m-%Y}) | +{config.points_open} |
| El monto estimado supera ${_number(config.amount_threshold)} | +{config.points_amount} |
| El organismo es de una región prioritaria | +{config.points_region} |
| El rubro oficial es uno de los rubros objetivo | +{config.points_category} |
| El texto contiene una palabra excluida | −{config.penalty_excluded} |

Prioridad alta desde {config.high_priority_from} puntos y media desde {config.medium_priority_from}.

**Qué tener presente.**

- Los puntos son de criterio, no aprendidos de los datos. Al contrastarlo con 100.124 licitaciones de 12 meses, la prioridad alta no se adjudicó más ni tuvo menos competencia que el resto. El puntaje ordena por parecido con el perfil; sirve para acortar la lista, no para decidir.
- Las palabras clave son un filtro débil: frente al rubro oficial de construcción y mantenimiento tienen 36 % de precisión y 35,5 % de cobertura. Los rubros objetivo son una señal más confiable.
- El perfil inicial es un ejemplo (servicios industriales y de construcción en el norte del país). Cámbialo en la barra lateral.
- En la muestra pública las palabras se buscan solo en el nombre de la licitación, porque la descripción no se publica.
- Cerca de la mitad de las licitaciones no informa monto estimado.

**Próximamente.** Alertas de licitaciones nuevas y reportes periódicos todavía no están implementados.
"""
    )


def main() -> None:
    """Render the dashboard."""

    st.set_page_config(page_title="Mercado Público Intelligence", layout="wide")
    st.title("Mercado Público Intelligence")
    st.caption("Exploración de licitaciones públicas de Chile y priorización con un puntaje por reglas.")

    path, source_label, default_reference = resolve_dataset()
    frame = _load(str(path))

    filtered, config, reference_date = _sidebar(frame, source_label, default_reference)
    if filtered.empty:
        st.warning("Ninguna licitación cumple los filtros seleccionados.")
        return

    scored = score_licitaciones(filtered, config=config, reference_date=str(reference_date))
    scored = add_competition(scored, load_competition())
    _kpis(scored)

    resumen, montos, oportunidades, tendencias, acerca = st.tabs(
        ["Resumen", "Montos", "Oportunidades", "Tendencias", "Acerca del puntaje"]
    )
    with resumen:
        _tab_resumen(scored)
    with montos:
        _tab_montos(scored)
    with oportunidades:
        _tab_oportunidades(scored)
    with tendencias:
        _tab_tendencias()
    with acerca:
        _tab_acerca(config, reference_date)


if __name__ == "__main__":
    main()
