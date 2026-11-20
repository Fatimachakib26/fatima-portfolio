"""Page 1 — Dashboard général (squelette de l'étape 1, sans données)."""
import streamlit as st

from components.theme import html

from components.kpi_cards import KPI, banner, card_title, chips, empty_state, kpi_row
from components.navbar import render_navbar
from config import ASSET_UNIVERSE

params = st.session_state["params"]
render_navbar("Dashboard", "Vue d'ensemble du portefeuille optimisé")

hero, perf = st.columns([1.05, 1], gap="medium")
with hero:
    html("""
        <div class="qi-hero">
          <div class="qi-hero-kicker">Modern Portfolio Theory · Markowitz 1952</div>
          <h1>Smart Portfolio Optimization<br>&amp; Risk Analytics</h1>
          <p>Sélectionnez vos actifs, estimez μ et Σ sur des données
          Yahoo Finance réelles et comparez les allocations optimales au S&amp;P 500.</p>
          <div class="qi-hero-badges">
            <span class="qi-hero-badge">Variance minimale</span>
            <span class="qi-hero-badge">Sharpe maximal</span>
            <span class="qi-hero-badge">Backtest hors échantillon</span>
          </div>
        </div>
        """)
with perf, st.container(border=True, height=330):
    card_title("Portefeuille vs S&P 500", f"Benchmark : {params.benchmark}")
    empty_state("Courbe de performance", "Disponible après le chargement des données (étape 2).", "📈")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
kpi_row([
    KPI("Rendement annualisé", None, icon="📈", help="Moyenne des rendements × périodes par an."),
    KPI("Volatilité annualisée", None, icon="🌊", help="Écart-type des rendements × √(périodes par an)."),
    KPI("Ratio de Sharpe", None, fmt="{:.2f}", icon="⚖️", help="(Rendement − taux sans risque) / volatilité."),
    KPI("Actifs sélectionnés", float(len(params.tickers)), fmt="{:.0f}", icon="🧩",
        foot=", ".join(params.tickers[:4]) + ("…" if len(params.tickers) > 4 else "")),
    KPI("Performance cumulée", None, icon="🚀", help="Valeur finale / valeur initiale − 1."),
])

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([1.35, 1, 1], gap="medium")
with c1, st.container(border=True):
    card_title("Frontière efficiente", "Rendement espéré vs volatilité")
    empty_state("Frontière de Markowitz", "Étape 5 — calculée par optimisation SLSQP.", "🎯")
with c2, st.container(border=True):
    card_title("Répartition du capital", "Portefeuille sélectionné")
    empty_state("Allocation", "Étape 4 — pondérations optimales.", "🍩")
with c3, st.container(border=True):
    card_title("Corrélations", "Matrice de corrélation des rendements")
    empty_state("Heatmap", "Étape 3 — estimée sur l'historique commun.", "🔥")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
with st.container(border=True):
    card_title("Univers sélectionné")
    st.markdown(chips([f"{t} · {ASSET_UNIVERSE.get(t, t)}" for t in params.tickers]),
                unsafe_allow_html=True)
banner("Étape 1 : interface et design system. Aucun chiffre financier n'est affiché tant que "
       "les données réelles ne sont pas téléchargées.", "info", "🧭")
