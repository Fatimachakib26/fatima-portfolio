"""Page — Analyse du risque (squelette de l'étape 1, sans données)."""
import streamlit as st

from components.kpi_cards import banner, card_title, empty_state
from components.navbar import render_navbar

render_navbar("Analyse du risque", "Volatilité, VaR, Expected Shortfall, drawdowns")

BLOCKS = [('Mesures de dispersion', 'Variance, écart-type, volatilité historique et glissante (21 / 63 j)', 'Étape 6'), ('Value at Risk', 'Historique, paramétrique (VaR.py du cours) et Monte-Carlo (VaRMonteCarlo.py), 95 % / 99 %', 'Étape 6'), ('Expected Shortfall & Max Drawdown', 'Perte moyenne au-delà de la VaR ; pire baisse depuis un sommet', 'Étape 6'), ('Visualisations', 'Heatmap, distribution des rendements vs loi normale, distribution des pertes', 'Étape 6')]

cols = st.columns(2, gap="medium")
for i, (name, detail, step) in enumerate(BLOCKS):
    with cols[i % 2], st.container(border=True):
        card_title(name, step)
        empty_state(detail, "Contenu calculé à partir des données réelles.", "🛰️")
banner("Page en construction : le contenu sera branché sur le moteur <code>core/</code> "
       "aux étapes indiquées.", "info", "🧭")
