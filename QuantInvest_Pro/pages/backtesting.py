"""Page — Backtesting (squelette de l'étape 1, sans données)."""
import streamlit as st

from components.kpi_cards import banner, card_title, empty_state
from components.navbar import render_navbar

render_navbar("Backtesting", "Walk-forward hors échantillon, frais inclus, sans biais d'anticipation")

BLOCKS = [('Séparation estimation / test', 'Fenêtre glissante [t−252, t−1] ou découpage A / B', 'Étape 6'), ('Rééquilibrage & frais', 'Mensuel / trimestriel / annuel ; frais = bps × rotation', 'Étape 6'), ('Comparaison', 'Markowitz vs équipondéré vs S&P 500 : CAGR, volatilité, Sharpe, Max DD', 'Étape 6'), ('Évolution du capital', 'Courbes de richesse et drawdowns', 'Étape 6')]

cols = st.columns(2, gap="medium")
for i, (name, detail, step) in enumerate(BLOCKS):
    with cols[i % 2], st.container(border=True):
        card_title(name, step)
        empty_state(detail, "Contenu calculé à partir des données réelles.", "🛰️")
banner("Page en construction : le contenu sera branché sur le moteur <code>core/</code> "
       "aux étapes indiquées.", "info", "🧭")
