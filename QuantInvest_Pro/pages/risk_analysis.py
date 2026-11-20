"""Page 3 — Analyse du risque.

Indicateurs de performance ajustée du risque (Sharpe, Sortino, Calmar),
mesures de perte extrême (VaR historique et paramétrique, CVaR, drawdown),
distribution des rendements et corrélation glissante entre actifs.
"""
import pandas as pd
import streamlit as st
from scipy import stats as sps

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
tabs = st.tabs(["📋 Indicateurs", "📊 Distribution des rendements", "🔗 Corrélation glissante"])

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
