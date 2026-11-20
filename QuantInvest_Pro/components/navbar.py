"""Barre supérieure : titre de page, statut des données, actualisation."""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from components.data_service import request_refresh
from components.theme import html

# Statuts possibles des données (renseignés par core/data_loader à l'étape 2)
_STATUS = {
    "idle": ("idle", "Données non chargées"),
    "live": ("live", "Yahoo Finance · en direct"),
    "cache": ("cache", "Données en cache"),
    "error": ("error", "Échec du téléchargement"),
}


def render_navbar(title: str, subtitle: str = "", crumb: str = "QuantInvest Pro") -> bool:
    """Affiche la barre supérieure. Retourne True si « Actualiser » est cliqué."""
    status = st.session_state.get("data_status", {"state": "idle", "fetched_at": None})
    dot, label = _STATUS.get(status.get("state", "idle"), _STATUS["idle"])
    fetched_at: datetime | None = status.get("fetched_at")
    stamp = fetched_at.strftime("%d/%m/%Y %H:%M") if fetched_at else "—"

    left, right, btn = st.columns([4.2, 5.2, 1.3], vertical_alignment="center")
    with left:
        html(f"""
            <div class="qi-navbar-title">
              <span class="qi-crumb">{crumb}</span>
              <span class="qi-page-title">{title}</span>
              {f'<span class="qi-page-sub">{subtitle}</span>' if subtitle else ''}
            </div>
            """)
    with right:
        html(f"""
            <div class="qi-navbar-right">
              <span class="qi-pill"><span class="qi-dot {dot}"></span>{label}</span>
              <span class="qi-pill">🕒 Mise à jour : {stamp}</span>
            </div>
            """)
    with btn:
        # on_click s'exécute avant la réexécution : app.py retélécharge alors les données
        clicked = st.button("⟳ Actualiser", key=f"refresh_{title}", width="stretch",
                            on_click=request_refresh, help="Forcer un nouveau téléchargement Yahoo Finance")
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    return clicked
