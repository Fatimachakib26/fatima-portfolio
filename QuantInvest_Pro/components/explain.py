"""Encadrés pédagogiques sous chaque graphique."""
from __future__ import annotations

import streamlit as st

from components.theme import html


def explain(how: str, takeaway: str) -> None:
    """« Comment lire » (méthode) et « À retenir » (chiffres calculés)."""
    html(f"""
        <div class="qi-explain">
          <div class="qi-explain-box how"><div class="qi-explain-t">📖 Comment lire</div><div>{how}</div></div>
          <div class="qi-explain-box key"><div class="qi-explain-t">💡 À retenir</div><div>{takeaway}</div></div>
        </div>
    """)


def section(title: str, subtitle: str = "") -> None:
    sub = f'<div class="qi-card-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="qi-card-title" style="margin-top:4px">{title}</div>{sub}', unsafe_allow_html=True)
