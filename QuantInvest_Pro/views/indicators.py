"""Page — Explorateur d'indicateurs : définition, calcul pas à pas, comparaison, évolution."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import PLOTLY_CONFIG, asset_colors, base_figure
from components.data_service import MarketBundle, render_data_alerts, source_text
from components.explain import explain, section
from components.formatting import num
from components.kpi_cards import banner, empty_state
from components.metric import details
from components.navbar import render_navbar
from components.state import get_market, get_params
from components.workspace import get_library, period_returns, portfolio_returns, selection_bar
from config import AppParams
from core.indicators import META, calculer_indicateurs
from core.trace import fr_val

params: AppParams = get_params()
bundle: MarketBundle = get_market()
render_navbar("Indicateurs", "Comprendre chaque indicateur, le recalculer et le comparer")
render_data_alerts(bundle)
if not bundle.ok:
    empty_state("Aucune donnée exploitable", "", "📡")
    st.stop()
library = get_library(params, bundle)
sel = selection_bar(library, bundle, params, show_assets=True)
assets_r, bench_r, ppy = period_returns(sel, bundle)
pr = portfolio_returns(sel.portfolios, library, assets_r, bench_r)
SRC, rf = source_text(bundle), params.risk_free_rate

c1, c2 = st.columns([1.4, 1])
cle = c1.selectbox("Indicateur", list(META), format_func=lambda k: META[k]["nom"], key="ind_key")
subjects = list(pr) + sel.assets
subject = c2.selectbox("Calcul détaillé pour", subjects, key="ind_subject")
meta = META[cle]


def series_of(s: str) -> tuple[pd.Series, pd.Series | None]:
    w = library[s].weights if s in library and library[s].type != "reference" else None
    return (pr[s] if s in pr else assets_r[s]), w


@st.cache_data(ttl=3600, show_spinner=False)
def _all(cle: str, data: dict, bench, rf: float, ppy: int, src: str, weights: dict):
    out = {}
    for s, r in data.items():
        res = calculer_indicateurs(r, bench, rf, ppy, poids=weights.get(s), source=src, sujet=s)
        if cle in res:
            out[s] = res[cle]
    return out


data = {s: series_of(s)[0] for s in subjects}
weights = {s: series_of(s)[1] for s in subjects if series_of(s)[1] is not None}
vals = _all(cle, data, bench_r, rf, ppy, SRC, weights)
if not vals:
    banner(f"« {meta['nom']} » n'est pas calculable pour cette sélection (indice de référence ou poids nécessaires).", "warn", "⚠️")
    st.stop()

with st.container(border=True):
    section(f"1. {meta['nom']} — définition et formule")
    st.markdown(meta["definition"])
    st.latex(meta["formule"])
if subject in vals:
    with st.container(border=True):
        section(f"2. Calcul pas à pas — {subject}", sel.label)
        details(vals[subject], "ind_detail")

order = pd.Series({s: v.valeur for s, v in vals.items()}).sort_values()
colors = {**asset_colors(list(bundle.assets)), **{n: library[n].couleur for n in pr}}
with st.container(border=True):
    section("3. Valeur pour chaque portefeuille et chaque actif", "Barres triées · portefeuilles en couleur pleine, actifs en clair")
    fig = base_figure("", 60 + 32 * len(order))
    fig.add_trace(go.Bar(x=order.values, y=order.index, orientation="h",
                         marker=dict(color=[colors.get(s, "#8E8FB5") for s in order.index],
                                     opacity=[1.0 if s in pr else 0.55 for s in order.index]),
                         text=[fr_val(v, meta["unite"]) for v in order.values], textposition="outside",
                         hovertemplate="%{y} : %{text}<extra></extra>"))
    if meta["unite"] == "pct":
        fig.update_xaxes(tickformat=".0%")
    fig.update_traces(cliponaxis=False)
    fig.update_layout(showlegend=False, margin=dict(l=10, r=90, t=10, b=10))
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

with st.container(border=True):
    section("4. Évolution glissante")
    win_lbl = st.segmented_control("Fenêtre", ["3 mois", "6 mois", "1 an"], default="6 mois", required=True, key="ind_win")
    win = {"3 mois": 63, "6 mois": 126, "1 an": 252}[win_lbl] * ppy // 252
    step = max(1, win // 20)

    @st.cache_data(ttl=3600, show_spinner=False)
    def _rolling(cle, r, bench, rf, ppy, win, step, w):
        out = {}
        for end in range(win, len(r) + 1, step):
            seg = r.iloc[end - win:end]
            b = bench.loc[seg.index] if bench is not None else None
            try:
                res = calculer_indicateurs(seg, b, rf, ppy, poids=w)
                if cle in res:
                    out[seg.index[-1]] = res[cle].valeur
            except ValueError:
                continue
        return pd.Series(out)

    fig = base_figure("", 340)
    shown = [s for s in list(pr)[:4] + ([subject] if subject not in pr else [])]
    with st.spinner("Calcul glissant…"):
        for s in shown:
            ser, w = series_of(s)
            roll = _rolling(cle, ser, bench_r, rf, ppy, win, step, w)
            if len(roll):
                fig.add_trace(go.Scatter(x=roll.index, y=roll.values, name=s, mode="lines",
                                         line=dict(color=colors.get(s, "#8E8FB5"), width=2)))
    if meta["unite"] == "pct":
        fig.update_yaxes(tickformat=".0%")
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=-0.15, yanchor="top", xanchor="left", x=0))
    if len(fig.data):
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    else:
        st.info("Période trop courte pour cette fenêtre.")

with st.container(border=True):
    section("5. Grille de lecture et 6. À retenir")
    top, bottom = order.index[-1], order.index[0]
    explain(f"{meta['lecture']}",
            f"Plus haute valeur : <b>{top}</b> ({fr_val(order[top], meta['unite'])}) ; plus basse : <b>{bottom}</b> "
            f"({fr_val(order[bottom], meta['unite'])}). Écart : {fr_val(order[top] - order[bottom], meta['unite'])}.<br>"
            f"<b>Limites</b> : {meta['limites']}")
