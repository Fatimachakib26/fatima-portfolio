"""Page 1 — Tableau de bord.

Verdict hors échantillon, indicateurs clés du portefeuille retenu, frontière,
allocation, corrélations et comparaison des trois portefeuilles du sujet.
"""
from dataclasses import replace
from datetime import date

import pandas as pd
import streamlit as st

from components import compute
from components.charts import (PLOTLY_CONFIG, base100_chart, corr_heatmap, donut_chart, frontier_chart,
                               sparkline)
from components.data_service import MarketBundle, render_data_alerts
from components.formatting import METRIC_HELP, format_metrics, num, pct
from components.kpi_cards import KPI, banner, card_title, empty_state, kpi_row
from components.navbar import render_navbar
from components.state import get_market, get_params
from components.theme import html
from config import ASSET_UNIVERSE, FREQUENCIES, OPTIMIZATION_OBJECTIVES, AppParams
from core.optimization import EQUAL, MAX_SHARPE, MIN_VAR
from core.returns import periodic_rf
from core.verdict import build_verdict

params: AppParams = get_params()
bundle: MarketBundle = get_market()

render_navbar("Tableau de bord", "Markowitz bat-il le 1/N hors échantillon ?")
render_data_alerts(bundle)

# --------------------------------------------------------------------------- #
# Verdict (résultats hors échantillon)
# --------------------------------------------------------------------------- #
res, verdict, split_error = None, None, None
if bundle.ok:
    try:
        res = compute.split_for(params, bundle.prices, bundle.periods_per_year)
        verdict = build_verdict(res.returns_test, res.metrics_test, res.portfolios[MAX_SHARPE].sharpe,
                                periodic_rf(params.risk_free_rate, bundle.periods_per_year),
                                res.returns_test.index[0], res.returns_test.index[-1])
    except ValueError as exc:
        split_error = str(exc)

if verdict is not None:
    v_col, k_col = st.columns([2.1, 1], gap="medium")
    badge = ('<span class="qi-badge sig">significatif</span>' if verdict.significant
             else '<span class="qi-badge nsig">non significatif</span>')
    with v_col:
        html(f"""
            <div class="qi-verdict">
              <div class="qi-verdict-k">⚖️ Verdict hors échantillon {badge}</div>
              <div class="qi-verdict-s">{verdict.sentence}</div>
            </div>
        """)
    with k_col:
        kpi_row([KPI("Meilleur Sharpe (test)", verdict.best_sharpe, fmt="{:.2f}", icon="🏆", foot=verdict.best_name)])
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        kpi_row([
            KPI("Pire drawdown", verdict.worst_drawdown, icon="📉", foot=verdict.worst_name,
                help=METRIC_HELP["Drawdown maximal"]),
            KPI("Annoncé − réalisé", verdict.announced - verdict.realized, fmt="{:+.2f}", icon="🎭",
                foot="Sharpe maximal", help="Sharpe promis sur la période d'estimation moins Sharpe obtenu en test."),
        ])
elif bundle.ok:
    banner("Le verdict hors échantillon n'est pas encore calculable : "
           + (split_error or "données insuffisantes")
           + " Réglez la <b>date de séparation</b> dans Paramètres pour lancer le calcul.", "info", "🧭")
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

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
        st.plotly_chart(base100_chart(bundle.prices, bundle.benchmark_prices, height=250, log_y=True),
                        width="stretch", config=PLOTLY_CONFIG)
    else:
        empty_state("Données indisponibles", "Vérifiez la connexion puis cliquez sur Actualiser.", "📡")

# --------------------------------------------------------------------------- #
# KPI du portefeuille retenu, sur la période de test (hors échantillon)
# --------------------------------------------------------------------------- #
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
retained = {"max_sharpe": MAX_SHARPE, "min_variance": MIN_VAR, "equal_weight": EQUAL}[params.objective]
m = res.metrics_test.loc[retained] if res is not None else None
foot = f"{OPTIMIZATION_OBJECTIVES[params.objective]} · période de test"
kpi_row([
    KPI("Rendement annualisé", m["Rendement annualisé"] if m is not None else None, icon="📈",
        help=METRIC_HELP["Rendement annualisé"], foot=foot, signed=True),
    KPI("Volatilité annualisée", m["Volatilité annualisée"] if m is not None else None, icon="🌊",
        help=METRIC_HELP["Volatilité annualisée"], foot=foot),
    KPI("Ratio de Sharpe", m["Sharpe"] if m is not None else None, fmt="{:.2f}", icon="⚖️",
        help=METRIC_HELP["Sharpe"], foot=foot),
    KPI("Actifs retenus", float(len(bundle.assets)), fmt="{:.0f}", icon="🧩",
        foot=f"sur {len(params.tickers)} sélectionnés"),
    KPI("Performance cumulée", m["Rendement cumulé"] if m is not None else None, icon="🚀",
        help=METRIC_HELP["Rendement cumulé"], foot=foot, signed=True),
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
                      <span style="font-family:var(--font-num);font-size:1.25rem;font-weight:700">{num(last)}</span>
                      <span class="{cls}" style="font-size:.8rem;font-weight:600">{arrow} {pct(chg, 2, signed=True)}</span>
                    </div>
                    <div class="qi-asset-name">{cur} · {period_label} · période {pct(total, 0, signed=True)}</div>
                """)
                tail = s.iloc[-spark_window:]
                st.plotly_chart(sparkline(tail, tail.iloc[-1] >= tail.iloc[0]), width="stretch",
                                config={"displayModeBar": False, "staticPlot": True}, key=f"spark_{t}")

# --------------------------------------------------------------------------- #
# Frontière, allocation, corrélations (période d'estimation)
# --------------------------------------------------------------------------- #
if res is not None:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    est, ports = res.est, res.portfolios
    c1, c2, c3 = st.columns([1.35, 1, 1], gap="medium")
    with c1, st.container(border=True):
        card_title("Frontière efficiente", f"Estimation {est.start:%m/%Y} – {est.end:%m/%Y} · plafond {pct(params.weight_max, 0)}")
        fr = compute.frontier(est.mu, est.cov, params.risk_free_rate, params.weight_min, params.weight_max)
        fig = frontier_chart(None, fr, ports, params.risk_free_rate, 330)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    with c2, st.container(border=True):
        card_title("Répartition du capital", OPTIMIZATION_OBJECTIVES[params.objective])
        st.plotly_chart(donut_chart(ports[retained].weights, 330), width="stretch", config=PLOTLY_CONFIG)
    with c3, st.container(border=True):
        card_title("Corrélations", "Rendements, période d'estimation")
        st.plotly_chart(corr_heatmap(est.corr, 330), width="stretch", config=PLOTLY_CONFIG)

    with st.container(border=True):
        card_title("Les trois portefeuilles du sujet", "Mêmes poids, estimés jusqu'à la date de séparation puis figés")
        cols = ["Rendement annualisé", "Volatilité annualisée", "Sharpe", "Drawdown maximal"]
        fmt = pd.concat({"Estimation": format_metrics(res.metrics_est[cols]),
                         "Test": format_metrics(res.metrics_test[cols])}, axis=1)
        fmt.columns = [f"{a} · {b}" for a, b in fmt.columns]
        st.dataframe(fmt, width="stretch")
elif bundle.ok:
    empty_state("Frontière et allocation indisponibles", split_error or "", "🎯")

if bundle.clean is not None:
    c = bundle.clean
    st.caption(f"Historique commun : {c.start:%d/%m/%Y} → {c.end:%d/%m/%Y} · {num(c.n_obs, 0)} séances · "
               f"fréquence {params.frequency.lower()} (facteur d'annualisation {FREQUENCIES[params.frequency][1]}) · "
               f"taux sans risque {pct(params.risk_free_rate)} · cours de clôture ajustés (dividendes et splits) · "
               "source Yahoo Finance.")
