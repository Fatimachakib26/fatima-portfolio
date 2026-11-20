"""Page 1 — Dashboard général.

Étape 2 : données réelles (filtres, performance base 100, cartes d'actifs).
Les KPI du portefeuille, la frontière et l'allocation arrivent aux étapes 3 à 5.
"""
from dataclasses import replace
from datetime import date

import streamlit as st

from components.state import get_market, get_params

from components.charts import PLOTLY_CONFIG, base100_chart, sparkline
from components.data_service import MarketBundle, render_data_alerts
from components.kpi_cards import KPI, banner, card_title, empty_state, kpi_row
from components.navbar import render_navbar
from components.theme import html
from config import ASSET_UNIVERSE, FREQUENCIES, AppParams

params: AppParams = get_params()
bundle: MarketBundle = get_market()

render_navbar("Tableau de bord", "Vue d'ensemble du portefeuille optimisé")
render_data_alerts(bundle)

# --------------------------------------------------------------------------- #
# Filtres : sélection des actifs et période
# --------------------------------------------------------------------------- #
with st.container(border=True):
    with st.form("dashboard_filters", border=False):
        options = list(dict.fromkeys([*ASSET_UNIVERSE, *params.tickers]))
        f1, f2, f3, f4 = st.columns([3.2, 1.1, 1.1, 0.9], vertical_alignment="bottom")
        sel = f1.multiselect("Actifs du portefeuille", options, default=params.tickers,
                             format_func=lambda t: f"{t} · {ASSET_UNIVERSE.get(t, t)}")
        start = f2.date_input("Du", params.start_date, min_value=date(2000, 1, 1), max_value=date.today(),
                              format="DD/MM/YYYY")
        end = f3.date_input("Au", params.end_date, min_value=date(2000, 1, 1), max_value=date.today(),
                            format="DD/MM/YYYY")
        apply = f4.form_submit_button("Appliquer", width="stretch")
    if apply:
        candidate = replace(params, tickers=sel, start_date=start, end_date=end)
        errors = candidate.validate()
        if errors:
            for e in errors:
                banner(e, "error", "⛔")
        else:
            st.session_state["params"] = candidate
            st.rerun()

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Bannière + performance comparée
# --------------------------------------------------------------------------- #
hero, perf = st.columns([1.05, 1], gap="medium")
with hero:
    html("""
        <div class="qi-hero">
          <div class="qi-hero-kicker">Modern Portfolio Theory · Markowitz 1952</div>
          <h1>Smart Portfolio Optimization<br>&amp; Risk Analytics</h1>
          <p>Sélectionnez vos actifs, estimez μ et Σ sur des données Yahoo Finance
          réelles et comparez les allocations optimales au S&amp;P 500.</p>
          <div class="qi-hero-badges">
            <span class="qi-hero-badge">Variance minimale</span>
            <span class="qi-hero-badge">Sharpe maximal</span>
            <span class="qi-hero-badge">Backtest hors échantillon</span>
          </div>
        </div>
    """)
with perf, st.container(border=True, height=330):
    bench_label = bundle.benchmark or params.benchmark
    card_title("Actifs vs S&P 500", f"Performance base 100 · benchmark {bench_label}")
    if bundle.ok:
        st.plotly_chart(base100_chart(bundle.prices, bundle.benchmark_prices, height=250),
                        width="stretch", config=PLOTLY_CONFIG)
    else:
        empty_state("Données indisponibles", "Vérifiez la connexion puis cliquez sur Actualiser.", "📡")

# --------------------------------------------------------------------------- #
# KPI (portefeuille : étapes 3-4)
# --------------------------------------------------------------------------- #
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
kpi_row([
    KPI("Rendement annualisé", None, icon="📈", help="Moyenne des rendements × périodes par an.", foot="Étape 3"),
    KPI("Volatilité annualisée", None, icon="🌊", help="Écart-type des rendements × √(périodes par an).", foot="Étape 3"),
    KPI("Ratio de Sharpe", None, fmt="{:.2f}", icon="⚖️", help="(Rendement − taux sans risque) / volatilité.", foot="Étape 4"),
    KPI("Actifs retenus", float(len(bundle.assets)), fmt="{:.0f}", icon="🧩",
        foot=f"sur {len(params.tickers)} sélectionnés"),
    KPI("Observations communes", float(bundle.clean.n_obs) if bundle.clean is not None else None,
        fmt="{:,.0f}", icon="🗓️", help="Nombre de dates où tous les actifs ont un prix.",
        foot=params.frequency.lower()),
])

# --------------------------------------------------------------------------- #
# Cartes d'actifs (style « ticker » de la référence)
# --------------------------------------------------------------------------- #
if bundle.ok:
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    prices = bundle.prices
    period_label = {"Quotidienne": "1 j", "Hebdomadaire": "1 sem.", "Mensuelle": "1 mois"}[params.frequency]
    spark_window = {"Quotidienne": 126, "Hebdomadaire": 26, "Mensuelle": 12}[params.frequency]
    per_row = 6
    for i in range(0, len(bundle.assets), per_row):
        cols = st.columns(per_row, gap="small")
        for col, t in zip(cols, bundle.assets[i:i + per_row]):
            s = prices[t]
            last, prev = float(s.iloc[-1]), float(s.iloc[-2])
            chg = last / prev - 1
            total = last / float(s.iloc[0]) - 1
            cur = bundle.raw.currencies.get(t) or ""
            cls = "qi-up" if chg >= 0 else "qi-down"
            arrow = "▲" if chg >= 0 else "▼"
            with col, st.container(border=True):
                html(f"""
                    <div class="qi-asset-sym">{t} <span class="qi-asset-name">{ASSET_UNIVERSE.get(t, '')}</span></div>
                    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:6px">
                      <span style="font-family:var(--font-num);font-size:1.25rem;font-weight:700">{last:,.2f}</span>
                      <span class="{cls}" style="font-size:.8rem;font-weight:600">{arrow} {chg:+.2%}</span>
                    </div>
                    <div class="qi-asset-name">{cur} · {period_label} · période {total:+.0%}</div>
                """)
                tail = s.iloc[-spark_window:]
                st.plotly_chart(sparkline(tail, tail.iloc[-1] >= tail.iloc[0]), width="stretch",
                                config={"displayModeBar": False, "staticPlot": True}, key=f"spark_{t}")

# --------------------------------------------------------------------------- #
# Analyses à venir
# --------------------------------------------------------------------------- #
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([1.35, 1, 1], gap="medium")
with c1, st.container(border=True):
    card_title("Frontière efficiente", "Rendement espéré vs volatilité")
    empty_state("Frontière de Markowitz", "Étape 5 — calculée par optimisation SLSQP.", "🎯")
with c2, st.container(border=True):
    card_title("Répartition du capital", "Portefeuille sélectionné")
    empty_state("Allocation", "Étape 4 — pondérations optimales.", "🍩")
with c3, st.container(border=True):
    card_title("Corrélations", "Matrice de corrélation des rendements")
    empty_state("Heatmap", "Étape 3 — estimée sur l'historique commun.", "🔥")

if bundle.clean is not None:
    c = bundle.clean
    st.caption(f"Historique commun : {c.start:%d/%m/%Y} → {c.end:%d/%m/%Y} · {c.n_obs:,} observations "
               f"({params.frequency.lower()}, facteur d'annualisation {FREQUENCIES[params.frequency][1]}) · "
               "cours de clôture ajustés (dividendes et splits) · source Yahoo Finance.")
