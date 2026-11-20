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
                               grouped_bars, sparkline, wealth_chart)
from components.explain import explain
from components.data_service import MarketBundle, render_data_alerts
from components.formatting import METRIC_HELP, format_metrics, num, pct
from components.kpi_cards import KPI, banner, card_title, empty_state, kpi_row
from components.navbar import render_navbar
from components.state import get_market, get_params
from components.theme import html
from config import ASSET_UNIVERSE, FREQUENCIES, OPTIMIZATION_OBJECTIVES, AppParams
from core.optimization import EQUAL, MAX_SHARPE, MIN_VAR
from core.portfolio import effective_n, metrics_table
from core.returns import simple_returns
from core.returns import periodic_rf
from core.verdict import build_verdict

params: AppParams = get_params()
bundle: MarketBundle = get_market()

render_navbar("Tableau de bord", "Markowitz bat-il le 1/N hors échantillon ?")
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
        kpi_row([KPI("Meilleur Sharpe", verdict.best_sharpe, fmt="{:.2f}", icon="🏆",
                     foot=f"{verdict.best_name} · période de test")])
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        kpi_row([
            KPI("Pire drawdown", verdict.worst_drawdown, icon="📉", foot=f"{verdict.worst_name} · période de test",
                help=METRIC_HELP["Drawdown maximal"]),
            KPI("Annoncé − réalisé", verdict.announced - verdict.realized, fmt="{:+.2f}", icon="🎭",
                foot="Sharpe maximal · période de test",
                help="Sharpe promis sur la période d'estimation moins Sharpe obtenu sur la période de test."),
        ])
elif bundle.ok:
    banner("Le verdict hors échantillon n'est pas encore calculable : "
           + (split_error or "données insuffisantes")
           + " Réglez la <b>date de séparation</b> dans Paramètres pour lancer le calcul.", "info", "🧭")
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# B1. Tableau comparatif des 3 portefeuilles et du S&P 500
# --------------------------------------------------------------------------- #
BEST_RULE = {"Rendement annualisé": "max", "Volatilité annualisée": "min", "Sharpe": "max", "Sortino": "max",
             "Drawdown maximal": "max", "Rendement cumulé": "max"}


def _styled(tab: pd.DataFrame, portfolios: list[str]):
    """Format français + meilleure valeur (parmi les portefeuilles) en vert."""
    fmt = format_metrics(tab)
    styles = pd.DataFrame("", index=tab.index, columns=tab.columns)
    for col, rule in BEST_RULE.items():
        vals = tab.loc[portfolios, col].astype(float)
        best = vals.idxmax() if rule == "max" else vals.idxmin()
        styles.loc[best, col] = "color:#22C55E;font-weight:700"
    return fmt.style.apply(lambda _: styles, axis=None)


if res is not None:
    ppy = bundle.periods_per_year
    cols = list(BEST_RULE)
    ports_names = [MIN_VAR, MAX_SHARPE, EQUAL]
    est_tab, test_tab = res.metrics_est[cols].copy(), res.metrics_test[cols].copy()
    bench_r = None
    if bundle.benchmark:
        bench_r = simple_returns(bundle.benchmark_prices)
        b_est = bench_r.loc[res.returns_est.index]
        b_test = bench_r.loc[res.returns_test.index]
        bm = metrics_table({f"{bundle.benchmark} (référence)": b_est}, params.risk_free_rate, ppy)[cols]
        bt_ = metrics_table({f"{bundle.benchmark} (référence)": b_test}, params.risk_free_rate, ppy)[cols]
        est_tab, test_tab = pd.concat([est_tab, bm]), pd.concat([test_tab, bt_])
    est_lbl = f"Estimation {res.est.start:%Y}–{res.est.end:%Y}"
    test_lbl = f"Test {res.returns_test.index[0]:%Y}–{res.returns_test.index[-1]:%Y}"
    with st.container(border=True):
        card_title("Les trois portefeuilles du sujet face au S&P 500",
                   "Poids estimés jusqu'à la date de séparation · estimation : poids constants · test : achat puis "
                   "conservation · en vert : meilleure valeur parmi les 3 portefeuilles")
        st.markdown(f"**{est_lbl}** ({res.est.start:%d/%m/%Y} – {res.est.end:%d/%m/%Y})")
        st.dataframe(_styled(est_tab, ports_names), width="stretch",
                     column_config={c: st.column_config.TextColumn(c, help=METRIC_HELP.get(c)) for c in cols})
        st.markdown(f"**{test_lbl}** ({res.returns_test.index[0]:%d/%m/%Y} – {res.returns_test.index[-1]:%d/%m/%Y})")
        st.dataframe(_styled(test_tab, ports_names), width="stretch",
                     column_config={c: st.column_config.TextColumn(c, help=METRIC_HELP.get(c)) for c in cols})
        best_test = test_tab.loc[ports_names, "Sharpe"].idxmax()
        drops = (est_tab.loc[ports_names, "Sharpe"] - test_tab.loc[ports_names, "Sharpe"])
        spy_txt = ""
        if bundle.benchmark:
            spy_name = f"{bundle.benchmark} (référence)"
            beat = [k for k in ports_names if test_tab.loc[k, "Sharpe"] > test_tab.loc[spy_name, "Sharpe"]]
            spy_txt = (f" Face au S&amp;P 500 (Sharpe {num(test_tab.loc[spy_name, 'Sharpe'])} en test), "
                       f"{len(beat)} portefeuille(s) sur 3 font mieux.")
        explain(
            "Les deux tableaux portent sur les mêmes poids. Le premier mesure ce que l'optimiseur a vu (il est "
            "optimisé pour y briller), le second ce qui s'est passé ensuite. Seul le second juge la méthode.",
            f"En estimation, le meilleur Sharpe est celui de <b>{est_tab.loc[ports_names, 'Sharpe'].idxmax()}</b> "
            f"({num(est_tab.loc[ports_names, 'Sharpe'].max())}). En test, c'est <b>{best_test}</b> "
            f"({num(test_tab.loc[best_test, 'Sharpe'])}). Le Sharpe maximal perd {num(drops[MAX_SHARPE])} point, "
            f"le 1/N {num(drops[EQUAL])}.{spy_txt}",
        )

# --------------------------------------------------------------------------- #
# B2. Valeur de 100 investis sur la période de test
# --------------------------------------------------------------------------- #
if res is not None:
    with st.container(border=True):
        card_title("Valeur de 100 investis sur la période de test",
                   "Achat à la date de séparation aux poids estimés, puis conservation (les poids dérivent avec les cours)")
        b = bench_r.loc[res.returns_test.index].rename(f"{bundle.benchmark}") if bench_r is not None else None
        st.plotly_chart(wealth_chart(res.returns_test, b, 420, baseline=True), width="stretch", config=PLOTLY_CONFIG)
        final = 100 * (1 + res.returns_test).prod()
        lead = final.idxmax()
        explain(
            "Chaque courbe suit la valeur de 100 investis le premier jour de la période de test. La ligne pointillée "
            "marque 100 : au-dessus, on gagne. Survolez le graphique pour lire toutes les valeurs à une même date.",
            "Valeur finale : " + " ; ".join(f"{k} <b>{num(v, 1)}</b>" for k, v in final.items())
            + (f" ; {bundle.benchmark} {num(100 * (1 + b).prod(), 1)}" if b is not None else "")
            + f". <b>{lead}</b> termine en tête.",
        )

# --------------------------------------------------------------------------- #
# Bannière + performance comparée
# --------------------------------------------------------------------------- #
hero, perf = st.columns([1.05, 1], gap="medium")
with hero:
    html("""
        <div class="qi-hero">
          <div class="qi-hero-kicker">Théorie moderne du portefeuille · Markowitz 1952</div>
          <h1>Optimisation de portefeuille<br>et analyse des risques</h1>
          <p>Sélectionnez vos actifs, estimez μ et Σ sur des données Yahoo Finance
          réelles et comparez les allocations optimales au S&amp;P 500.</p>
          <div class="qi-hero-badges">
            <span class="qi-hero-badge">Variance minimale</span>
            <span class="qi-hero-badge">Sharpe maximal</span>
            <span class="qi-hero-badge">Test hors échantillon</span>
          </div>
        </div>
    """)
with perf, st.container(border=True, height=330):
    bench_label = bundle.benchmark or params.benchmark
    card_title("Actifs vs S&P 500", f"Performance base 100 · référence {bench_label}")
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
w_shown = res.portfolios[retained].weights if res is not None else None
foot = f"{OPTIMIZATION_OBJECTIVES[params.objective]} · période de test"
kpi_row([
    KPI("Rendement annualisé", m["Rendement annualisé"] if m is not None else None, icon="📈",
        help=METRIC_HELP["Rendement annualisé"], foot=foot, signed=True),
    KPI("Volatilité annualisée", m["Volatilité annualisée"] if m is not None else None, icon="🌊",
        help=METRIC_HELP["Volatilité annualisée"], foot=foot),
    KPI("Ratio de Sharpe", m["Sharpe"] if m is not None else None, fmt="{:.2f}", icon="⚖️",
        help=METRIC_HELP["Sharpe"], foot=foot),
    KPI("Actifs retenus", float((w_shown > 0.005).sum()) if w_shown is not None else None, fmt="{:.0f}", icon="🧩",
        foot=(f"poids > 0,5 % sur {len(bundle.assets)} · nombre effectif {num(effective_n(w_shown), 1)}"
              if w_shown is not None else f"sur {len(params.tickers)} sélectionnés"),
        help="Actifs détenus à plus de 0,5 % dans le portefeuille affiché. Nombre effectif de titres = 1 / Σw² : "
             "nombre d'actifs « équivalents » réellement détenus."),
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
# Frontière, comparaison des poids (B4), allocation, corrélations
# --------------------------------------------------------------------------- #
if res is not None:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    est, ports = res.est, res.portfolios
    c1, c2 = st.columns([1.15, 1], gap="medium")
    with c1, st.container(border=True):
        card_title("Frontière efficiente", f"Estimation {est.start:%m/%Y} – {est.end:%m/%Y} · plafond {pct(params.weight_max, 0)}")
        fr = compute.frontier(est.mu, est.cov, params.risk_free_rate, params.weight_min, params.weight_max)
        fig = frontier_chart(None, fr, ports, params.risk_free_rate, 440,
                             assets=pd.DataFrame({"rendement": est.mu, "volatilite": est.vol}))
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    with c2, st.container(border=True):
        card_title("Comparaison des pondérations", f"Ligne rouge : plafond de {pct(params.weight_max, 0)} par actif")
        wdf = pd.DataFrame({k: p.weights for k, p in ports.items()})
        st.plotly_chart(grouped_bars(wdf, 360, colors=["#22D3EE", "#A855F7", "#F59E0B"], y_title="Poids",
                                     hline=params.weight_max, hline_label=f"plafond {pct(params.weight_max, 0)}"),
                        width="stretch", config=PLOTLY_CONFIG)
        capped = {k: [a for a, v in p.weights.items() if v >= params.weight_max - 1e-4]
                  for k, p in ports.items() if k != EQUAL}
        txt = " ; ".join(f"{k} : <b>{', '.join(v)}</b>" for k, v in capped.items() if v)
        explain("Pour chaque actif, une barre par portefeuille. Une barre qui touche la ligne rouge est bloquée par "
                "le plafond : sans lui, l'optimiseur aurait investi davantage.",
                ("Actifs bloqués au plafond — " + txt + "." if txt else "Aucun actif n'atteint le plafond.")
                + f" Le 1/N donne {pct(1 / len(bundle.assets), 1)} à chacun.")
    c3, c4 = st.columns([1, 1.15], gap="medium")
    with c3, st.container(border=True):
        card_title("Répartition du capital", OPTIMIZATION_OBJECTIVES[params.objective])
        st.plotly_chart(donut_chart(ports[retained].weights, 330), width="stretch", config=PLOTLY_CONFIG)
    with c4, st.container(border=True):
        card_title("Corrélations", "Rendements, période d'estimation · échelle de 0 à 1")
        st.plotly_chart(corr_heatmap(est.corr, 360), width="stretch", config=PLOTLY_CONFIG)
elif bundle.ok:
    empty_state("Frontière et allocation indisponibles", split_error or "", "🎯")

if bundle.clean is not None:
    c = bundle.clean
    st.caption(f"Historique commun : {c.start:%d/%m/%Y} → {c.end:%d/%m/%Y} · {num(c.n_obs, 0)} séances · "
               f"fréquence {params.frequency.lower()} (facteur d'annualisation {FREQUENCIES[params.frequency][1]}) · "
               f"taux sans risque {pct(params.risk_free_rate)} · cours de clôture ajustés (dividendes et splits) · "
               "source Yahoo Finance.")
