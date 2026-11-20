"""Cartes KPI et blocs HTML réutilisables (bannières, états vides)."""
from __future__ import annotations

import html
from dataclasses import dataclass

import streamlit as st


@dataclass
class KPI:
    label: str
    value: float | None          # None = donnée indisponible (jamais inventée)
    fmt: str = "{:.2%}"
    icon: str = "📈"
    help: str = ""               # explication affichée en infobulle
    foot: str = ""
    signed: bool = False         # colorer en vert / rouge selon le signe


def _kpi_html(k: KPI) -> str:
    if k.value is None:
        value_html = '<div class="qi-kpi-value pending">—</div>'
    else:
        cls = ""
        if k.signed:
            cls = "qi-up" if k.value >= 0 else "qi-down"
        value_html = f'<div class="qi-kpi-value {cls}">{k.fmt.format(k.value)}</div>'
    label = html.escape(k.label)
    if k.help:
        label = f'<span class="qi-help" title="{html.escape(k.help)}">{label}</span>'
    foot = f'<div class="qi-kpi-foot">{k.foot}</div>' if k.foot else ""
    return f"""
    <div class="qi-kpi">
      <div class="qi-kpi-head"><span class="qi-kpi-label">{label}</span>
      <span class="qi-kpi-icon">{k.icon}</span></div>
      {value_html}{foot}
    </div>"""


def kpi_row(kpis: list[KPI]) -> None:
    """Affiche une rangée de KPI en colonnes égales."""
    for col, k in zip(st.columns(len(kpis)), kpis):
        col.markdown(_kpi_html(k), unsafe_allow_html=True)


def banner(text: str, kind: str = "info", icon: str = "ℹ️") -> None:
    """Bandeau d'information : kind ∈ {info, warn, error, ok}."""
    st.markdown(f'<div class="qi-banner {kind}"><span>{icon}</span><div>{text}</div></div>',
                unsafe_allow_html=True)


def empty_state(title: str, detail: str = "", icon: str = "🛰️") -> None:
    """Zone vide explicite : affichée tant que les données réelles manquent."""
    st.markdown(
        f'<div class="qi-empty"><div class="qi-empty-icon">{icon}</div>'
        f'<b>{title}</b><br><span style="font-size:.84rem">{detail}</span></div>',
        unsafe_allow_html=True,
    )


def card_title(title: str, subtitle: str = "") -> None:
    sub = f'<div class="qi-card-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="qi-card-title">{title}</div>{sub}', unsafe_allow_html=True)


def chips(items: list[str]) -> str:
    return "".join(f'<span class="qi-chip">{html.escape(i)}</span>' for i in items)
