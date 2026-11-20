"""Page — Analyse des actifs (squelette de l'étape 1, sans données)."""
import streamlit as st

from components.kpi_cards import banner, card_title, empty_state
from components.navbar import render_navbar

render_navbar("Analyse des actifs", "Étude individuelle et comparaison des actions")

BLOCKS = [('Prix & rendements', 'Prix ajustés, rendements journaliers, performance cumulée', 'Étape 3'), ('Statistiques descriptives', 'Moyenne, écart-type, skewness, kurtosis, test de normalité', 'Étape 3'), ('CAPM', 'Bêta et alpha vs benchmark (CAPM.py du cours)', 'Étape 6'), ('Comparaison interactive', 'Performance base 100 de plusieurs actions', 'Étape 7')]

cols = st.columns(2, gap="medium")
for i, (name, detail, step) in enumerate(BLOCKS):
    with cols[i % 2], st.container(border=True):
        card_title(name, step)
        empty_state(detail, "Contenu calculé à partir des données réelles.", "🛰️")
banner("Page en construction : le contenu sera branché sur le moteur <code>core/</code> "
       "aux étapes indiquées.", "info", "🧭")
