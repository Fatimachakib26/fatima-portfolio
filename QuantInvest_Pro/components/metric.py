"""
Carte d'indicateur traçable : la valeur, puis « ⓘ D'où vient ce chiffre ? »
(définition, formule, entrées, calcul détaillé, source, période, données).
"""
from __future__ import annotations

import html as _html

import pandas as pd
import streamlit as st

from components.theme import html
from core.reporting import to_csv_bytes
from core.trace import Resultat


def _card(res: Resultat, icon: str, foot: str, signed: bool, title: str | None) -> str:
    cls = ""
    if signed and res.valeur == res.valeur:  # pas NaN
        cls = "qi-up" if res.valeur >= 0 else "qi-down"
    value = res.texte
    if signed and res.valeur == res.valeur and res.valeur > 0 and res.unite in ("pct", "ratio"):
        value = "+" + value
    label = _html.escape(title or res.nom)
    return f"""
    <div class="qi-kpi qi-kpi-trace">
      <div class="qi-kpi-head"><span class="qi-kpi-label">{label}</span><span class="qi-kpi-icon">{icon}</span></div>
      <div class="qi-kpi-value {cls}">{value}</div>
      <div class="qi-kpi-foot">{_html.escape(foot or res.sujet)}</div>
    </div>"""


def details(res: Resultat, key: str) -> None:
    """Contenu détaillé (utilisé dans le popover, réutilisable ailleurs)."""
    st.markdown(f"**{res.nom}**" + (f" — {res.sujet}" if res.sujet else ""))
    st.caption(res.definition)
    st.latex(res.formule)
    if res.entrees:
        st.markdown("**Données d'entrée**")
        st.dataframe(pd.DataFrame({"Entrée": [e.nom for e in res.entrees], "Valeur": [e.texte for e in res.entrees]}),
                     hide_index=True, width="stretch")
    st.markdown("**Calcul détaillé**")
    for step in res.etapes:
        st.markdown(f"- {step}")
    st.markdown(f"**Résultat : {res.texte}**")
    st.markdown(f"**Source** : {res.source}  \n**Période** : {res.periode}")
    if res.lecture:
        st.markdown(f"**Grille de lecture** : {res.lecture}")
    if res.limites:
        st.markdown(f"**Limites** : {res.limites}")
    if res.donnees is not None and len(res.donnees):
        if st.toggle("Voir les données", key=f"data_{key}"):
            st.dataframe(res.donnees, width="stretch", height=240)
            st.download_button("⬇️ Exporter ces données (CSV)",
                               to_csv_bytes(res.donnees.rename_axis(res.donnees.index.name or "date").reset_index()),
                               f"{res.cle}_{res.sujet or 'donnees'}.csv".replace(" ", "_"), "text/csv", key=f"dl_{key}")


def afficher_metrique(res: Resultat | None, key: str, icon: str = "📊", foot: str = "", signed: bool = False,
                      title: str | None = None) -> None:
    """Carte + bouton de traçabilité. `key` doit être unique dans la page."""
    if res is None:
        html(f'<div class="qi-kpi"><div class="qi-kpi-head"><span class="qi-kpi-label">{_html.escape(title or "")}'
             f'</span><span class="qi-kpi-icon">{icon}</span></div><div class="qi-kpi-value pending">—</div>'
             f'<div class="qi-kpi-foot">{_html.escape(foot)}</div></div>')
        return
    html(_card(res, icon, foot, signed, title))
    with st.popover("ⓘ D'où vient ce chiffre ?", width="stretch"):
        details(res, key)


def metric_row(items: list[dict]) -> None:
    """items : liste de kwargs pour afficher_metrique."""
    for col, kw in zip(st.columns(len(items)), items):
        with col:
            afficher_metrique(**kw)
