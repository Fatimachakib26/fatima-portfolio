"""Navigation latérale fixe (logo, liens vers les 6 pages, pied de page)."""
from __future__ import annotations

import streamlit as st

from components.theme import LOGO_SVG, html
from config import APP_NAME, INSTITUTION, VERSION

SHORT_LABELS = {
    "Optimisation Markowitz": "Optimisation",
    "Analyse du risque": "Risque",
    "Test rétrospectif": "Test rétrospectif",
    "Analyse des actifs": "Actifs",
    "Paramètres & méthodologie": "Paramètres",
}


def render_sidebar(pages: list) -> None:
    """Affiche la sidebar personnalisée.

    Les liens utilisent st.page_link : la navigation reste interne à Streamlit
    (pas de rechargement complet), donc l'état de session est conservé.
    """
    with st.sidebar:
        html(f"""
            <div class="qi-brand">
              {LOGO_SVG}
              <div>
                <div class="qi-brand-name">{APP_NAME}</div>
                <div class="qi-brand-tag">Analyse de portefeuille</div>
              </div>
            </div>
            <div class="qi-nav-label">Navigation</div>
            """)
        for page in pages:
            # libellé court dans le menu ; le titre complet est dans la barre supérieure
            st.page_link(page, label=SHORT_LABELS.get(page.title, page.title), icon=page.icon)

        params = st.session_state.get("params")
        n_assets = len(params.tickers) if params else 0
        html(f"""
            <div class="qi-side-foot">
              <b>{n_assets}</b> actifs sélectionnés<br>
              Référence : <b>{params.benchmark if params else "—"}</b><br>
              <span style="opacity:.8">{INSTITUTION}<br>v{VERSION}</span>
            </div>
            """)
