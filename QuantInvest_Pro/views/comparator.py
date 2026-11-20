"""Page — Comparateur de portefeuilles."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import PLOTLY_CONFIG, drawdown_chart, grouped_bars, wealth_chart
from components.data_service import MarketBundle, render_data_alerts, source_text
from components.explain import explain, section
from components.formatting import num, pct
from components.kpi_cards import banner, empty_state
from components.metric import details
from components.navbar import render_navbar
from components.state import get_market, get_params
from components.workspace import get_library, period_returns, portfolio_returns, selection_bar
from config import AppParams
from core.indicators import META, calculer_indicateurs
from core.portfolio import risk_contributions
from core.reporting import to_csv_bytes
from core.returns import periodic_rf
from core.stats_tests import memmel_test
from core.trace import fr_val

params: AppParams = get_params()
bundle: MarketBundle = get_market()
render_navbar("Comparateur", "Tous les indicateurs, côte à côte, pour les portefeuilles choisis")
render_data_alerts(bundle)
if not bundle.ok:
    empty_state("Aucune donnée exploitable", "", "📡")
    st.stop()
library = get_library(params, bundle)
sel = selection_bar(library, bundle, params)
if len(sel.portfolios) < 2:
    banner("Sélectionnez au moins 2 portefeuilles dans la barre ci-dessus.", "info", "🧭")
    st.stop()
assets_r, bench_r, ppy = period_returns(sel, bundle)
pr = portfolio_returns(sel.portfolios, library, assets_r, bench_r)
names = list(pr)
SRC = source_text(bundle)
rf = params.risk_free_rate
IND = {n: calculer_indicateurs(pr[n], bench_r, rf, ppy,
                               poids=None if library[n].type == "reference" else library[n].weights,
                               source=SRC, sujet=n, nom_benchmark=bundle.benchmark or "SPY") for n in names}
colors = {n: library[n].couleur for n in names}

# ------------------------------------------------------------------ Tableau
HIGHER = {"rendement_annualise", "rendement_cumule", "sharpe", "sortino", "calmar", "ratio_information", "treynor",
          "drawdown_max", "alpha_jensen", "asymetrie", "nombre_effectif"}
LOWER = {"volatilite", "duree_drawdown", "var95_hist", "var99_hist", "var95_param", "var99_param", "cvar95",
         "tracking_error", "kurtosis", "rotation"}
keys = [k for k in META if any(k in IND[n] for n in names)]
num_tab = pd.DataFrame({META[k]["nom"]: [IND[n][k].valeur if k in IND[n] else np.nan for n in names] for k in keys}, index=names)
txt_tab = pd.DataFrame({META[k]["nom"]: [IND[n][k].texte if k in IND[n] else "—" for n in names] for k in keys}, index=names)
styles = pd.DataFrame("", index=names, columns=txt_tab.columns)
for k in keys:
    col = META[k]["nom"]
    v = num_tab[col]
    if v.notna().sum() < 2 or (k not in HIGHER and k not in LOWER):
        continue
    best, worst = (v.idxmax(), v.idxmin()) if k in HIGHER else (v.idxmin(), v.idxmax())
    styles.loc[best, col] = "color:#22C55E;font-weight:700"
    styles.loc[worst, col] = "color:#F43F5E"
with st.container(border=True):
    section(f"Tableau des indicateurs — {sel.label}", "Vert : meilleure valeur · rouge : moins bonne · neutre pour bêta et corrélation")
    st.dataframe(txt_tab.T.style.apply(lambda _: styles.T, axis=None), width="stretch", height=760)
    c1, c2, c3 = st.columns([1.2, 1.2, 1])
    k_sel = c1.selectbox("ⓘ D'où vient ce chiffre ? — indicateur", keys, format_func=lambda k: META[k]["nom"], key="cmp_k")
    n_sel = c2.selectbox("Portefeuille", names, key="cmp_n")
    long = num_tab.rename_axis("portefeuille").reset_index().melt(id_vars="portefeuille", var_name="indicateur", value_name="valeur")
    long.insert(0, "periode", sel.label)
    c3.download_button("⬇️ Exporter (CSV, format long)", to_csv_bytes(long), "comparaison_portefeuilles.csv",
                       "text/csv", width="stretch")
    if k_sel in IND[n_sel]:
        with st.expander(f"Détail : {META[k_sel]['nom']} — {n_sel}", expanded=True):
            details(IND[n_sel][k_sel], "cmp_detail")

# ------------------------------------------------------------------ Radar
def _norm(series: pd.Series, higher=True) -> pd.Series:
    lo, hi = series.min(), series.max()
    s = (series - lo) / (hi - lo) if hi > lo else series * 0 + 0.5
    return s if higher else 1 - s


axes = {"Rendement": _norm(num_tab["Rendement annualisé"]), "Sharpe": _norm(num_tab["Ratio de Sharpe"]),
        "Sortino": _norm(num_tab["Ratio de Sortino"]), "Faible volatilité": _norm(num_tab["Volatilité annualisée"], False),
        "Faible drawdown": _norm(num_tab["Drawdown maximal"]),
        "Diversification": _norm(num_tab.get("Nombre effectif de titres", pd.Series(1.0, index=names)).fillna(1.0))}
c1, c2 = st.columns([1, 1.25], gap="medium")
with c1, st.container(border=True):
    section("Profil comparé", "Chaque axe ramené entre 0 (le moins bon) et 1 (le meilleur) parmi la sélection")
    fig = go.Figure()
    cats = list(axes) + [list(axes)[0]]
    for n in names:
        vals = [axes[a][n] for a in axes] + [axes[list(axes)[0]][n]]
        fig.add_trace(go.Scatterpolar(r=vals, theta=cats, name=n, line=dict(color=colors[n], width=2), fill="toself",
                                      opacity=0.55, hovertemplate=f"<b>{n}</b><br>%{{theta}} : %{{r:.2f}}<extra></extra>"))
    fig.update_layout(height=420, polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 1], showticklabels=False,
                      gridcolor="rgba(142,143,181,0.2)"), angularaxis=dict(gridcolor="rgba(142,143,181,0.2)")),
                      legend=dict(orientation="h", y=-0.1, yanchor="top", xanchor="left", x=0), margin=dict(l=30, r=30, t=20, b=10))
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    score = pd.DataFrame(axes).mean(axis=1).sort_values(ascending=False)
    explain("Plus la surface est grande, meilleur est le profil global. Les axes sont relatifs à la sélection.",
            f"Profil le plus équilibré : <b>{score.index[0]}</b> (score moyen {num(score.iloc[0])} sur 1).")
with c2, st.container(border=True):
    section("Valeur de 100 investis et drawdown", sel.label)
    df = pd.DataFrame(pr)
    st.plotly_chart(wealth_chart(df, None, 300, baseline=True), width="stretch", config=PLOTLY_CONFIG)
    st.plotly_chart(drawdown_chart(df, 200), width="stretch", config=PLOTLY_CONFIG)

# ------------------------------------------------------------------ Poids et risques
opt = [n for n in names if library[n].type != "reference"]
if opt:
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        section("Pondérations côte à côte")
        st.plotly_chart(grouped_bars(pd.DataFrame({n: library[n].weights for n in opt}).fillna(0), 320,
                                     colors=[colors[n] for n in opt], y_title="Poids"), width="stretch", config=PLOTLY_CONFIG)
    with c2, st.container(border=True):
        section("Part du risque total par actif", "Covariance de la période sélectionnée")
        cov = assets_r.cov() * ppy
        st.plotly_chart(grouped_bars(pd.DataFrame({n: risk_contributions(library[n].weights, cov)["Part du risque"]
                                                   for n in opt}), 320, colors=[colors[n] for n in opt]),
                        width="stretch", config=PLOTLY_CONFIG)

# ------------------------------------------------------------------ Corrélations et Memmel
c1, c2 = st.columns(2, gap="medium")
corr = pd.DataFrame(pr).corr()
with c1, st.container(border=True):
    section("Corrélation des portefeuilles entre eux")
    st.plotly_chart(go.Figure(go.Heatmap(z=corr.values, x=names, y=names, zmin=0, zmax=1,
                                         colorscale=[[0, "#0B0B24"], [0.6, "#5B21B6"], [1, "#C026D3"]],
                                         text=[[f"{v:.2f}".replace(".", ",") for v in r_] for r_ in corr.values],
                                         texttemplate="%{text}", hovertemplate="%{y} / %{x} : %{z:.2f}<extra></extra>"))
                    .update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(autorange="reversed")),
                    width="stretch", config=PLOTLY_CONFIG)
rf_p = periodic_rf(rf, ppy)
pv = pd.DataFrame(np.nan, index=names, columns=names)
for a in names:
    for b in names:
        if a != b:
            pv.loc[a, b] = memmel_test(pr[a], pr[b], rf_p)["p_value"]
with c2, st.container(border=True):
    section("Test de Memmel : p-valeurs par paire", "Rouge : p < 0,05, différence de Sharpe significative")
    st.dataframe(pv.map(lambda v: "—" if pd.isna(v) else num(v, 3)).style.apply(
        lambda col: ["color:#F43F5E;font-weight:700" if (not pd.isna(pv.loc[i, col.name]) and pv.loc[i, col.name] < 0.05) else ""
                     for i in col.index], axis=0), width="stretch")
best = num_tab["Ratio de Sharpe"].idxmax()
n_sig = int((pv < 0.05).sum().sum() / 2)
off = corr.where(~np.eye(len(names), dtype=bool)).stack()
explain("La corrélation mesure si deux portefeuilles montent et baissent ensemble ; le test de Memmel dit si leurs "
        "Sharpe diffèrent vraiment, compte tenu du hasard.",
        f"Meilleur Sharpe : <b>{best}</b> ({num(num_tab.loc[best, 'Ratio de Sharpe'])}). {n_sig} paire(s) sur "
        f"{len(names) * (len(names) - 1) // 2} ont un écart significatif. Corrélation moyenne entre portefeuilles : "
        f"{num(off.mean())} — " + ("ils se ressemblent beaucoup : les différences de méthode pèsent peu face au marché."
                                   if off.mean() > 0.85 else "ils offrent des profils réellement différents."))

# ------------------------------------------------------------------ Navigation et rapport
c1, c2 = st.columns([2, 1], gap="medium")
with c1, st.container(border=True):
    section("Ouvrir une fiche")
    pick = st.pills("Portefeuille", names, key="cmp_open_p", selection_mode="single")
    if pick:
        st.session_state["focus_portfolio"] = pick
        st.session_state["cmp_open_p"] = None
        st.switch_page("views/portfolios.py")
    pick_a = st.pills("Actif", bundle.assets, key="cmp_open_a", selection_mode="single")
    if pick_a:
        st.session_state["focus_asset"] = pick_a
        st.session_state["cmp_open_a"] = None
        st.switch_page("views/asset_analysis.py")
with c2, st.container(border=True):
    section("Rapport", "Page HTML autonome : tableau, graphiques interactifs, verdict, hypothèses, sources")
    if st.button("📄 Générer le rapport", key="cmp_report", width="stretch"):
        from core.report import build_html
        from core.verdict import fr_num
        best_s = num_tab["Ratio de Sharpe"].idxmax()
        verdict_txt = (f"Sur la période {sel.label}, le meilleur Sharpe est celui de <b>{best_s}</b> "
                       f"({fr_num(num_tab.loc[best_s, 'Ratio de Sharpe'])}). {n_sig} paire(s) de portefeuilles présentent "
                       "un écart de Sharpe statistiquement significatif (test de Memmel, seuil 5 %).")
        figs = {"Valeur de 100 investis": wealth_chart(pd.DataFrame(pr), None, 420, baseline=True),
                "Drawdown": drawdown_chart(pd.DataFrame(pr), 300)}
        html_doc = build_html(f"QuantInvest Pro — comparaison de portefeuilles", verdict_txt,
                              {"Indicateurs": txt_tab.T, "Pondérations": pd.DataFrame({n: library[n].weights for n in opt}).fillna(0).map(lambda v: pct(v, 1)) if opt else pd.DataFrame(),
                               "p-valeurs du test de Memmel": pv.map(lambda v: "—" if pd.isna(v) else num(v, 3))},
                              figs,
                              ["Poids estimés jusqu'à la date de séparation puis figés (achat puis conservation).",
                               "Rendements simples, annualisation × 252 et × √252.", f"Taux sans risque {pct(rf)} par an.",
                               "Biais du survivant : actions choisies a posteriori.", "Une seule période d'évaluation."],
                              [SRC, "Indicateurs : core/indicators.py (formules dans la page Sources et méthodologie)."])
        st.session_state["cmp_report_html"] = html_doc
    if st.session_state.get("cmp_report_html"):
        st.download_button("⬇️ Télécharger le rapport (HTML)", st.session_state["cmp_report_html"].encode("utf-8"),
                           "rapport_quantinvest.html", "text/html", width="stretch", key="cmp_report_dl")
