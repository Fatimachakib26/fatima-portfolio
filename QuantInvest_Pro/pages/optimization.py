"""Page — Optimisation Markowitz (squelette de l'étape 1, sans données)."""
import streamlit as st

from components.kpi_cards import banner, card_title, empty_state
from components.navbar import render_navbar

render_navbar("Optimisation Markowitz", "Cœur mathématique : min wᵀΣw sous contraintes")

BLOCKS = [('Rendements & matrices', 'Rendements journaliers, μ annualisé, Σ (empirique ou Ledoit-Wolf), corrélations', 'Étape 3'), ('Optimiseur SLSQP', 'Variance minimale, Sharpe maximal, équipondéré ; Σw = 1, bornes modifiables', 'Étape 4'), ('Frontière efficiente', 'Frontière exacte + nuage Monte-Carlo, infobulles par portefeuille', 'Étape 5'), ('Allocation optimale', 'Donut, tableau des poids, exports CSV / Excel', 'Étape 5')]

cols = st.columns(2, gap="medium")
for i, (name, detail, step) in enumerate(BLOCKS):
    with cols[i % 2], st.container(border=True):
        card_title(name, step)
        empty_state(detail, "Contenu calculé à partir des données réelles.", "🛰️")
banner("Page en construction : le contenu sera branché sur le moteur <code>core/</code> "
       "aux étapes indiquées.", "info", "🧭")
