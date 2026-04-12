"""Initial Streamlit dashboard placeholder."""

from __future__ import annotations

import streamlit as st


def main() -> None:
    """Render an initial dashboard placeholder."""
    st.set_page_config(page_title="Mercado Publico Intelligence", layout="wide")
    st.title("Mercado Publico Intelligence")
    st.caption("Dashboard MVP en construccion para monitoreo de licitaciones.")
    st.info("La vista analitica se implementara en la siguiente etapa del proyecto.")


if __name__ == "__main__":
    main()
