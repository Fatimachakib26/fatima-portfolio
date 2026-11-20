"""
QuantInvest Pro — point d'entrée.

Lancement :  streamlit run app.py

Rôle de ce fichier :
  1. configurer la page et appliquer le thème (CSS + template Plotly) ;
  2. initialiser l'état de session (paramètres utilisateur, statut des données) ;
  3. déclarer les 6 pages avec st.navigation (menu natif masqué) et afficher
     la sidebar personnalisée ;
  4. charger les données de marché (cache + statut) ;
  5. exécuter la page sélectionnée.
"""
from __future__ import annotations

import streamlit as st

from components.data_service import load_market_data
from components.sidebar import render_sidebar
from components.theme import apply_theme
from config import APP_NAME, LOGO_PATH, AppParams

st.set_page_config(
    page_title=f"{APP_NAME} · Optimisation de portefeuille",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "💠",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()


def init_state() -> None:
    """Valeurs initiales, créées une seule fois par session utilisateur."""
    st.session_state.setdefault("params", AppParams())
    st.session_state.setdefault("data_status", {"state": "idle", "fetched_at": None, "source": None})


init_state()

PAGES = [
    st.Page("views/dashboard.py", title="Tableau de bord", icon=":material/space_dashboard:", default=True),
    st.Page("views/portfolios.py", title="Portefeuilles", icon=":material/folder_special:"),
    st.Page("views/comparator.py", title="Comparateur", icon=":material/compare_arrows:"),
    st.Page("views/indicators.py", title="Indicateurs", icon=":material/functions:"),
    st.Page("views/optimization.py", title="Optimisation Markowitz", icon=":material/hub:"),
    st.Page("views/risk_analysis.py", title="Analyse du risque", icon=":material/shield:"),
    st.Page("views/backtesting.py", title="Test rétrospectif", icon=":material/history:"),
    st.Page("views/asset_analysis.py", title="Analyse des actifs", icon=":material/candlestick_chart:"),
    st.Page("views/settings.py", title="Paramètres & méthodologie", icon=":material/tune:"),
]

current = st.navigation(PAGES, position="hidden")
render_sidebar(PAGES)
# Données chargées une fois par exécution (cache mémoire) et partagées par les pages
st.session_state["market"] = load_market_data(st.session_state["params"])
current.run()
