"""
Thème visuel : injection du CSS global et template Plotly « quantinvest ».

Tous les graphiques de l'application héritent de ce template afin de garantir
une cohérence visuelle (fond transparent, grille discrète, palette néon).
"""
from __future__ import annotations

import re

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from config import COLORS, SERIES_COLORS, STYLE_PATH

TEMPLATE_NAME = "quantinvest"

# Logo vectoriel (hexagone en dégradé, inspiré de la référence) — réutilisé
# dans la sidebar ; assets/logo.png en est la version matricielle (PDF).
LOGO_SVG = """
<svg class="qi-brand-logo" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="qiA" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#EC4899"/><stop offset="1" stop-color="#A855F7"/>
    </linearGradient>
    <linearGradient id="qiB" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#7C3AED"/><stop offset="1" stop-color="#3B82F6"/>
    </linearGradient>
  </defs>
  <polygon points="32,4 56,18 32,32 8,18" fill="url(#qiA)"/>
  <polygon points="8,18 32,32 32,60 8,46" fill="url(#qiB)"/>
  <polygon points="56,18 56,46 32,60 32,32" fill="#22D3EE" opacity="0.85"/>
  <polyline points="14,42 22,36 29,40 38,28 50,22" fill="none" stroke="#fff"
            stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity="0.95"/>
</svg>
"""


def html(markup: str) -> None:
    """Affiche du HTML brut. Les retours à la ligne indentés sont aplatis :
    sinon le moteur Markdown de Streamlit interprète une ligne indentée de
    4 espaces comme un bloc de code."""
    st.markdown(re.sub(r"\n\s*", " ", markup.strip()), unsafe_allow_html=True)


def inject_css() -> None:
    """Charge assets/style.css dans la page (appelé une fois par exécution)."""
    try:
        css = STYLE_PATH.read_text(encoding="utf-8")
    except OSError as exc:  # l'application reste utilisable sans le thème
        st.warning(f"Feuille de style introuvable ({exc}).")
        return
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def register_plotly_template() -> None:
    """Déclare le template Plotly et en fait le template par défaut."""
    if TEMPLATE_NAME in pio.templates and pio.templates.default == TEMPLATE_NAME:
        return
    axis = dict(
        gridcolor=COLORS["grid"],
        zerolinecolor=COLORS["grid"],
        linecolor=COLORS["grid"],
        tickfont=dict(color=COLORS["muted"], size=11),
        title=dict(font=dict(color=COLORS["muted"], size=12)),
        showspikes=True,
        spikecolor=COLORS["violet2"],
        spikethickness=1,
        spikedash="dot",
    )
    pio.templates[TEMPLATE_NAME] = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Inter, sans-serif", color=COLORS["text"], size=12),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=SERIES_COLORS,
            xaxis=axis,
            yaxis=axis,
            margin=dict(l=10, r=10, t=40, b=10),
            hoverlabel=dict(
                bgcolor="#161743",
                bordercolor=COLORS["violet"],
                font=dict(family="Inter, sans-serif", color="#fff", size=12),
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(color=COLORS["muted"]),
                orientation="h",
                yanchor="bottom", y=1.02, xanchor="right", x=1,
            ),
            title=dict(font=dict(family="Space Grotesk, sans-serif", size=15, color=COLORS["text"])),
            colorscale=dict(
                sequential=[[0, "#0F1030"], [0.5, "#7C3AED"], [1, "#22D3EE"]],
                diverging=[[0, "#F43F5E"], [0.5, "#161743"], [1, "#8B5CF6"]],
            ),
        )
    )
    pio.templates.default = TEMPLATE_NAME


def apply_theme() -> None:
    inject_css()
    register_plotly_template()
