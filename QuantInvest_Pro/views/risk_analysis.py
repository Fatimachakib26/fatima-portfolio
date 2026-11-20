"""Page 3 — Analyse du risque.

Indicateurs de performance ajustée du risque (Sharpe, Sortino, Calmar),
mesures de perte extrême (VaR historique et paramétrique, CVaR, drawdown),
distribution des rendements et corrélation glissante entre actifs.
"""
import pandas as pd
import streamlit as st
from scipy import stats as sps
import numpy as np

from components import compute
from components.charts import PLOTLY_CONFIG, distribution_chart, rolling_corr_chart
from components.data_service import MarketBundle, render_data_alerts
from components.explain import explain, section
from components.formatting import METRIC_HELP, format_metrics, num, pct
from components.kpi_cards import banner, empty_state
from components.navbar import render_navbar
from components.state import get_market, get_params
from config import CRISES, AppParams
from core.optimization import EQUAL, MAX_SHARPE, MIN_VAR

params: AppParams = get_params()
bundle: MarketBundle = get_market()
render_navbar("Analyse du risque", "Pertes extrêmes, performance ajustée du risque et corrélations")
render_data_alerts(bundle)
if not bundle.ok:
    empty_state("Aucune donnée exploitable", "Cliquez sur Actualiser ou modifiez la sélection d'actifs.", "📡")
    st.stop()

ppy = bundle.periods_per_year
try:
    res = compute.split_for(params, bundle.prices, ppy)
except ValueError as exc:
    banner(str(exc), "error", "⛔")
    st.stop()

period_lbl = {"Quotidienne": "1 jour", "Hebdomadaire": "1 semaine", "Mensuelle": "1 mois"}[params.frequency]
tabs = st.tabs(["📋 Indicateurs", "📊 Distribution des rendements", "🔗 Corrélation glissante", "🧨 Scénarios"])

# --------------------------------------------------------------------------- #
with tabs[0]:
    cols = ["Rendement annualisé", "Volatilité annualisée", "Sharpe", "Sortino", "Calmar", "Drawdown maximal",
            "VaR 95 % historique", "CVaR 95 %", "VaR 95 % paramétrique", "Rendement cumulé"]
    tab = pd.concat({"Estimation": res.metrics_est[cols], "Test": res.metrics_test[cols]})
    perf_cols = ["Rendement annualisé", "Volatilité annualisée", "Sharpe", "Sortino", "Calmar", "Rendement cumulé"]
    loss_cols = ["Drawdown maximal", "VaR 95 % historique", "CVaR 95 %", "VaR 95 % paramétrique"]
    with st.container(border=True):
        section("Indicateurs par portefeuille et par période",
                f"Estimation : {res.est.start:%d/%m/%Y} – {res.est.end:%d/%m/%Y} · Test : "
                f"{res.returns_test.index[0]:%d/%m/%Y} – {res.returns_test.index[-1]:%d/%m/%Y} · taux sans risque "
                f"{pct(params.risk_free_rate)} · survolez un en-tête de colonne pour sa définition")
        fmt = format_metrics(tab)
        st.markdown("**Performance ajustée du risque**")
        st.dataframe(fmt[perf_cols], width="stretch",
                     column_config={c: st.column_config.TextColumn(c, help=METRIC_HELP.get(c)) for c in perf_cols})
        st.markdown(f"**Pertes extrêmes** (sur {period_lbl}, niveau de confiance 95 %)")
        st.dataframe(fmt[loss_cols], width="stretch",
                     column_config={c: st.column_config.TextColumn(c, help=METRIC_HELP.get(c)) for c in loss_cols})
        mt = res.metrics_test
        under = [(k, mt.loc[k, "VaR 95 % paramétrique"], mt.loc[k, "VaR 95 % historique"]) for k in mt.index]
        n_under = sum(p < h for _, p, h in under)
        worst = max(under, key=lambda x: x[2] - x[1])
        sortino_best = mt["Sortino"].idxmax()
        calmar_best = mt["Calmar"].idxmax()
        explain(
            "Chaque ligne est un portefeuille, sur la période d'estimation (où il a été optimisé) puis sur la "
            "période de test (jamais vue par l'optimiseur). Les VaR et CVaR sont des pertes : 2 % signifie "
            f"« perdre 2 % en {period_lbl} ». Comparer la VaR historique et la VaR paramétrique révèle si la loi "
            "normale décrit bien les pertes.",
            f"Hors échantillon, la VaR normale <b>{'sous-estime' if n_under else 'ne sous-estime pas'}</b> le risque "
            f"pour {n_under} portefeuille(s) sur {len(under)} "
            f"(ex. {worst[0]} : {pct(worst[1])} en loi normale contre {pct(worst[2])} observé). "
            f"Meilleur Sortino : <b>{sortino_best}</b> ({num(mt.loc[sortino_best, 'Sortino'])}) ; meilleur Calmar : "
            f"<b>{calmar_best}</b> ({num(mt.loc[calmar_best, 'Calmar'])}). La CVaR rappelle qu'au-delà de la VaR, "
            f"la perte moyenne atteint {pct(mt['CVaR 95 %'].max())} pour le portefeuille le plus exposé.",
        )

# --------------------------------------------------------------------------- #
with tabs[1]:
    c1, c2 = st.columns(2)
    which = c1.selectbox("Portefeuille", [MAX_SHARPE, MIN_VAR, EQUAL], key="dist_port")
    period = c2.radio("Période", ["Test", "Estimation"], horizontal=True, key="dist_period")
    r = (res.returns_test if period == "Test" else res.returns_est)[which]
    m = (res.metrics_test if period == "Test" else res.metrics_est).loc[which]
    with st.container(border=True):
        section(f"Distribution des rendements — {which}", f"Période {period.lower()} · {num(len(r), 0)} observations")
        st.plotly_chart(distribution_chart(r, m["VaR 95 % historique"], m["VaR 95 % paramétrique"], 400),
                        width="stretch", config=PLOTLY_CONFIG)
        skew, kurt = float(sps.skew(r)), float(sps.kurtosis(r))  # kurtosis en excès (0 pour la loi normale)
        jb = sps.jarque_bera(r)
        extreme = float((r < r.mean() - 3 * r.std()).mean())
        explain(
            "L'histogramme montre la fréquence de chaque rendement ; la courbe cyan est la loi normale de même "
            "moyenne et de même écart-type (hypothèse du modèle de Markowitz et de VaR.py). Les lignes verticales "
            "marquent les deux VaR à 95 %.",
            f"Asymétrie {num(skew)} et excès de kurtosis <b>{num(kurt)}</b> (0 pour une loi normale) : "
            f"{'queues épaisses — les pertes extrêmes sont plus fréquentes que prévu par la loi normale' if kurt > 1 else 'distribution proche de la normale'}. "
            f"Pertes au-delà de 3 écarts-types : {pct(extreme, 2)} des séances contre 0,13 % attendu. "
            f"Test de Jarque-Bera : p {'< 0,0001' if jb.pvalue < 1e-4 else '= ' + num(jb.pvalue, 4)} → normalité "
            f"{'rejetée' if jb.pvalue < 0.05 else 'non rejetée'} au seuil de 5 %.",
        )

# --------------------------------------------------------------------------- #
with tabs[2]:
    window = st.slider("Fenêtre glissante (séances)", 21, 252, params.corr_window, 21, key="corr_win",
                       help="Nombre de séances utilisées pour chaque calcul de corrélation (63 ≈ 3 mois).")
    rc = compute.rolling_corr(bundle.daily_prices, window)
    with st.container(border=True):
        section("Corrélation moyenne entre les actifs", f"Moyenne des {len(bundle.assets) * (len(bundle.assets) - 1) // 2} "
                f"paires, fenêtre de {window} séances · zones grisées : périodes de crise")
        st.plotly_chart(rolling_corr_chart(rc, CRISES, 400), width="stretch", config=PLOTLY_CONFIG)
        in_crisis = pd.Series(False, index=rc.index)
        for _, a, b in CRISES:
            in_crisis |= (rc.index >= pd.Timestamp(a)) & (rc.index <= pd.Timestamp(b))
        crisis_means = {label: rc.loc[a:b] for label, a, b in CRISES if len(rc.loc[a:b])}
        calm = rc[~in_crisis]
        takeaway = f"Hors crise, la corrélation moyenne vaut <b>{num(calm.mean())}</b>. " if len(calm) else ""
        if crisis_means:
            takeaway += " ; ".join(f"{k} : <b>{num(v.mean())}</b> (pic {num(v.max())})"
                                   for k, v in crisis_means.items()) + ". "
            if len(calm) and max(v.mean() for v in crisis_means.values()) > calm.mean():
                takeaway += ("Les corrélations montent quand les marchés chutent : la diversification protège "
                             "le moins précisément quand on en a le plus besoin.")
        else:
            takeaway += "Aucune période de crise répertoriée dans l'historique chargé."
        explain(
            "Chaque point est la corrélation moyenne entre toutes les paires d'actifs, calculée sur les "
            f"{window} séances précédentes. Plus elle est haute, plus les actifs bougent ensemble et moins la "
            "diversification protège.",
            takeaway,
        )

# --------------------------------------------------------------------------- #
with tabs[3]:
    from components.charts import base_figure
    from components.workspace import get_library
    from core import library as lib_
    from core.indicators import calculer_indicateurs
    from core.returns import simple_returns
    from core.scenarios import monte_carlo, shock_loss, stress_table
    import plotly.graph_objects as go

    library = get_library(params, bundle)
    names = st.multiselect("Portefeuilles", list(library), default=[n for n in st.session_state.get("sel_portfolios", [])
                           if n in library][:4] or list(library)[:3], key="sc_ports")
    full = simple_returns(bundle.clean.prices)
    b_full = full[bundle.benchmark] if bundle.benchmark else None
    series = {n: lib_.entry_returns(library[n], full[bundle.assets], b_full) for n in names}
    if not series:
        st.stop()
    with st.container(border=True):
        section("Tests de résistance historiques", "Poids de la bibliothèque appliqués à tout l'historique (achat puis conservation)")
        stt = stress_table(series)
        show = stt.copy()
        for c in show.columns:
            show[c] = show[c].map(lambda v: v.strftime("%d/%m/%Y") if hasattr(v, "strftime") else pct(v, 1))
        st.dataframe(show, width="stretch")
        worst = stt["Pire mois"].idxmin()
        explain("Rendement cumulé pendant chaque crise, pire semaine (5 séances) et pire mois (21 séances) glissants.",
                f"Pire mois : <b>{worst}</b> ({pct(stt.loc[worst, 'Pire mois'], 1)}, terminé le "
                f"{stt.loc[worst, 'Date (mois)']:%d/%m/%Y}). Attention : 2020 et 2022 sont dans la période d'estimation "
                "des portefeuilles optimisés, qui « connaissaient » ces crises.")
    with st.container(border=True):
        section("Choc hypothétique", "Perte estimée de chaque portefeuille à partir de son bêta (estimé sur toute la période)")
        c1, c2 = st.columns(2)
        shock = c1.slider(f"Baisse de {bundle.benchmark or 'l’indice'} (%)", 0, 40, 10, 1, key="sc_shock") / -100
        vshock = c2.slider("Hausse de la volatilité (%)", 0, 200, 50, 10, key="sc_vol") / 100
        rows = []
        for n, r_ in series.items():
            ind = calculer_indicateurs(r_, b_full, params.risk_free_rate, 252, sujet=n)
            beta = ind["beta"].valeur if "beta" in ind else 1.0
            out = shock_loss(beta, shock, ind["volatilite"].valeur, vshock)
            rows.append({"Portefeuille": n, "Bêta": num(beta), "Perte attendue": pct(out["perte_attendue"], 1),
                         "Perte au pire (95 %)": pct(out["perte_95"], 1),
                         "Calcul": f"{num(beta)} × ({pct(shock, 0)}) = {pct(out['perte_attendue'], 1)} ; "
                                   f"− 1,645 × {pct(out['sigma_jour'], 2)} (σ jour choquée) = {pct(out['perte_95'], 1)}"})
        st.dataframe(pd.DataFrame(rows).set_index("Portefeuille"), width="stretch")
        explain("Perte attendue = bêta × choc de marché. Perte au pire (95 %) : on retire 1,645 écart-type quotidien, "
                "augmenté du choc de volatilité. Modèle à un facteur : le risque propre à chaque action est ignoré.",
                f"Pour une baisse de {pct(-shock, 0)} du marché, le portefeuille le plus exposé perdrait environ "
                f"{max(rows, key=lambda x: float(x['Bêta'].replace(',', '.').replace('−', '-')))['Perte attendue']}.")
    with st.container(border=True):
        section("Monte-Carlo sur 1 an", "1 000 trajectoires, graine 42 · μ et σ estimés sur la période d'estimation")
        n_mc = st.selectbox("Portefeuille", list(series), key="sc_mc")
        r_est = series[n_mc].loc[:pd.Timestamp(params.split_date)]
        mu_a, sig_a = float(r_est.mean() * 252), float(r_est.std() * np.sqrt(252))
        cone, p_loss = monte_carlo(mu_a, sig_a)
        fig = base_figure("", 360)
        fig.add_trace(go.Scatter(x=cone.index, y=cone["P95"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=cone.index, y=cone["P5"], fill="tonexty", fillcolor="rgba(168,85,247,0.2)",
                                 line=dict(width=0), name="Entre 5 % et 95 %"))
        fig.add_trace(go.Scatter(x=cone.index, y=cone["P50"], line=dict(color="#A855F7", width=2.5), name="Médiane"))
        fig.add_hline(y=100, line=dict(color="#8E8FB5", dash="dot"))
        fig.update_layout(xaxis_title="Séances", yaxis_title="Valeur de 100 investis", hovermode="x unified")
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
        explain("Chaque trajectoire tire 252 rendements quotidiens d'une loi normale de moyenne μ/252 et d'écart-type "
                "σ/√252 (généralisation de GBM.py du cours). Le cône contient 90 % des trajectoires.",
                f"μ = {pct(mu_a, 1)}, σ = {pct(sig_a, 1)} : dans un an, médiane {num(cone['P50'].iloc[-1], 0)}, "
                f"pessimiste (5 %) {num(cone['P5'].iloc[-1], 0)}, optimiste (95 %) {num(cone['P95'].iloc[-1], 0)}. "
                f"Probabilité de perte : <b>{pct(p_loss, 1)}</b>. Hypothèses : rendements normaux et indépendants, μ "
                "et σ constants — les queues épaisses observées rendent le scénario pessimiste trop optimiste.")
