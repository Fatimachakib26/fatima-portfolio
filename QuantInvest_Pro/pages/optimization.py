"""Page 2 — Optimisation de Markowitz (cœur mathématique).

Toutes les estimations portent sur la PÉRIODE D'ESTIMATION (début → date de
séparation) : la période de test est réservée à la validation.
"""
import pandas as pd
import streamlit as st

from components.state import get_market, get_params

from components import compute
from components.charts import (PLOTLY_CONFIG, corr_heatmap, donut_chart, frontier_chart, grouped_bars)
from components.data_service import MarketBundle, render_data_alerts
from components.explain import explain, section
from components.formatting import format_metrics, num, pct, weights_table
from components.kpi_cards import KPI, banner, empty_state, kpi_row
from components.navbar import render_navbar
from config import COV_METHODS, AppParams
from core.optimization import EQUAL, MAX_SHARPE, MIN_VAR
from core.portfolio import risk_contributions
from core.reporting import to_csv_bytes, to_excel_bytes

params: AppParams = get_params()
bundle: MarketBundle = get_market()
render_navbar("Optimisation Markowitz", "Estimation de μ et Σ, portefeuilles optimaux et frontière efficiente")
render_data_alerts(bundle)
if not bundle.ok:
    empty_state("Aucune donnée exploitable", "Cliquez sur Actualiser ou modifiez la sélection d'actifs.", "📡")
    st.stop()

ppy, rf, cap = bundle.periods_per_year, params.risk_free_rate, params.weight_max
try:
    with st.spinner("Optimisation en cours…"):
        res = compute.split_for(params, bundle.prices, ppy)
        res_free = compute.split_for(params, bundle.prices, ppy, hi=1.0)
except ValueError as exc:
    banner(str(exc), "error", "⛔")
    st.stop()

est, ports = res.est, res.portfolios
for name, p in ports.items():
    if not p.converged:
        banner(f"<b>{name}</b> : {p.message}. Les poids affichés peuvent ne pas être optimaux.", "warn", "⚠️")

st.caption(f"Période d'estimation : {est.start:%d/%m/%Y} → {est.end:%d/%m/%Y} · {num(est.n_obs, 0)} observations "
           f"({params.frequency.lower()}, ×{ppy}) · {COV_METHODS[est.method]} · taux sans risque {pct(rf)} · "
           f"poids entre {pct(params.weight_min, 0)} et {pct(cap, 0)}")

tabs = st.tabs(["🧮 Données et estimation", "🎯 Portefeuilles optimaux", "📈 Frontière efficiente",
                "🧩 Contribution au risque", "🛡️ Ledoit-Wolf"])

# --------------------------------------------------------------------------- #
with tabs[0]:
    stats = pd.DataFrame({
        "Rendement moyen annualisé": est.mu,
        "Volatilité annualisée": est.vol,
        "Sharpe individuel": (est.mu - rf) / est.vol,
    }).sort_values("Sharpe individuel", ascending=False)
    c1, c2 = st.columns([1, 1.15], gap="medium")
    with c1, st.container(border=True):
        section("Rendements et volatilités annualisés", f"μ = moyenne × {ppy} · σ = écart-type × √{ppy}")
        st.dataframe(pd.DataFrame({
            "Rendement moyen annualisé": stats.iloc[:, 0].map(pct),
            "Volatilité annualisée": stats.iloc[:, 1].map(pct),
            "Sharpe individuel": stats.iloc[:, 2].map(num),
        }), width="stretch")
        best, worst = stats.index[0], stats.index[-1]
        explain(
            "Chaque ligne résume un actif sur la période d'estimation : son rendement moyen, son risque "
            "(volatilité) et leur rapport (Sharpe, net du taux sans risque).",
            f"<b>{best}</b> a le meilleur couple rendement / risque (Sharpe {num(stats.iloc[0, 2])}), "
            f"<b>{worst}</b> le moins bon ({num(stats.iloc[-1, 2])}). L'optimiseur va naturellement favoriser "
            f"les premiers — si ces moyennes historiques se répètent.",
        )
    with c2, st.container(border=True):
        section("Matrice des corrélations", "Heatmap des corrélations des rendements")
        st.plotly_chart(corr_heatmap(est.corr, 360), width="stretch", config=PLOTLY_CONFIG)
        pairs = est.corr.stack()
        pairs = pairs[[a < b for a, b in pairs.index]]
        hi_pair, lo_pair = pairs.idxmax(), pairs.idxmin()
        explain(
            "Une corrélation proche de 1 signifie que deux actifs montent et baissent ensemble ; "
            "proche de 0, leurs variations sont indépendantes. La diversification vient des faibles corrélations.",
            f"Corrélation moyenne : <b>{num(pairs.mean())}</b>. Paire la plus liée : <b>{hi_pair[0]}–{hi_pair[1]}</b> "
            f"({num(pairs.max())}) ; la moins liée : <b>{lo_pair[0]}–{lo_pair[1]}</b> ({num(pairs.min())}).",
        )
    with st.expander("Matrice de covariance annualisée Σ"):
        st.dataframe(est.cov.map(lambda v: num(v, 4)), width="stretch")

# --------------------------------------------------------------------------- #
with tabs[1]:
    kpi_row([
        KPI(f"{MIN_VAR} · volatilité", ports[MIN_VAR].volatility, icon="🛡️",
            foot=f"rendement espéré {pct(ports[MIN_VAR].expected_return)}"),
        KPI(f"{MAX_SHARPE} · Sharpe", ports[MAX_SHARPE].sharpe, fmt="{:.2f}", icon="⭐",
            foot=f"rendement {pct(ports[MAX_SHARPE].expected_return)} · volatilité {pct(ports[MAX_SHARPE].volatility)}"),
        KPI("1/N · Sharpe", ports[EQUAL].sharpe, fmt="{:.2f}", icon="⚖️",
            foot=f"rendement {pct(ports[EQUAL].expected_return)} · volatilité {pct(ports[EQUAL].volatility)}"),
    ])
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 1], gap="medium")
    with c1, st.container(border=True):
        section("Pondérations optimales", f"Plafond {pct(cap, 0)} par actif, sans vente à découvert")
        st.dataframe(weights_table({k: p.weights for k, p in ports.items()}), width="stretch")
        summary = pd.DataFrame({k: {"Rendement espéré": p.expected_return, "Volatilité": p.volatility,
                                    "Sharpe": p.sharpe} for k, p in ports.items()}).T
        st.dataframe(pd.DataFrame({"Rendement espéré": summary.iloc[:, 0].map(pct),
                                   "Volatilité": summary.iloc[:, 1].map(pct),
                                   "Sharpe": summary.iloc[:, 2].map(num)}), width="stretch")
        w_export = pd.DataFrame({k: p.weights for k, p in ports.items()})
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Allocations (CSV)", to_csv_bytes(w_export.rename_axis("actif").reset_index()),
                           "allocations_markowitz.csv", "text/csv", width="stretch")
        d2.download_button("⬇️ Allocations (Excel)", to_excel_bytes({"Allocations": w_export, "Synthese": summary}),
                           "allocations_markowitz.xlsx", width="stretch")
    with c2, st.container(border=True):
        choice = st.selectbox("Portefeuille", list(ports), index=1, key="donut_choice")
        st.plotly_chart(donut_chart(ports[choice].weights), width="stretch", config=PLOTLY_CONFIG)
        w = ports[choice].weights
        explain("Chaque part de l'anneau est la fraction du capital investie dans un actif.",
                f"<b>{choice}</b> : {int((w > 0.005).sum())} actifs sur {len(w)} ; le premier, "
                f"<b>{w.idxmax()}</b>, pèse {pct(w.max(), 1)}.")

    with st.container(border=True):
        section("Effet du plafond de poids", f"Poids avec plafond de {pct(cap, 0)} et sans plafond (100 %)")
        which = st.radio("Portefeuille", [MAX_SHARPE, MIN_VAR], horizontal=True, key="cap_cmp")
        cmp_df = pd.DataFrame({f"Avec plafond {pct(cap, 0)}": res.portfolios[which].weights,
                               "Sans plafond": res_free.portfolios[which].weights})
        st.plotly_chart(grouped_bars(cmp_df, 340, colors=["#A855F7", "#22D3EE"], y_title="Poids"),
                        width="stretch", config=PLOTLY_CONFIG)
        free, capd = res_free.portfolios[which], res.portfolios[which]
        top = free.weights.idxmax()
        explain(
            "Chaque paire de barres compare le poids d'un actif avec et sans plafond. Sans plafond, "
            "l'optimiseur peut concentrer le capital sur quelques actifs.",
            f"Sans plafond, <b>{top}</b> reçoit {pct(free.weights.max(), 1)} du capital ; le plafond le ramène à "
            f"{pct(capd.weights[top], 1)}. Coût annoncé du plafond : Sharpe {num(free.sharpe)} → {num(capd.sharpe)}"
            f" (estimation). Le test rétrospectif dira si cette diversification forcée paie hors échantillon.",
        )

# --------------------------------------------------------------------------- #
with tabs[2]:
    with st.container(border=True):
        section("Frontière efficiente de Markowitz", "Portefeuilles admissibles, frontière exacte et portefeuilles remarquables")
        cl = compute.cloud(est.mu, est.cov, rf, params.n_simulations, params.weight_min, cap)
        fr = compute.frontier(est.mu, est.cov, rf, params.weight_min, cap)
        st.plotly_chart(frontier_chart(cl, fr, ports, rf, 520), width="stretch", config=PLOTLY_CONFIG)
        if not fr["converged"].all():
            banner(f"{int((~fr['converged']).sum())} point(s) de la frontière n'ont pas convergé.", "warn", "⚠️")
        explain(
            "Chaque point est un portefeuille (axe horizontal : risque, axe vertical : rendement espéré). "
            "La courbe blanche est la frontière : le rendement maximal pour chaque niveau de risque. "
            "La droite pointillée part du taux sans risque et touche la frontière au portefeuille de Sharpe maximal.",
            f"Le Sharpe maximal ({num(ports[MAX_SHARPE].sharpe)}) domine le 1/N ({num(ports[EQUAL].sharpe)}) "
            f"<i>sur la période d'estimation</i> — c'est vrai par construction. Aucun des "
            f"{num(len(cl), 0)} portefeuilles aléatoires ne fait mieux (meilleur : {num(cl['sharpe'].max())}).",
        )

# --------------------------------------------------------------------------- #
with tabs[3]:
    with st.container(border=True):
        section("Contribution de chaque actif au risque total",
                "RCᵢ = wᵢ (Σw)ᵢ / σₚ · part du risque = RCᵢ / σₚ (somme = 100 %)")
        choice = st.selectbox("Portefeuille", list(ports), index=1, key="rc_choice")
        rc = risk_contributions(ports[choice].weights, est.cov)
        st.plotly_chart(grouped_bars(rc[["Poids", "Part du risque"]].rename(
            columns={"Poids": "Poids dans le portefeuille", "Part du risque": "Part du risque total"}), 360),
            width="stretch", config=PLOTLY_CONFIG)
        gap = (rc["Part du risque"] - rc["Poids"])
        hot = gap.idxmax()
        explain(
            "Pour chaque actif : à gauche sa part du capital, à droite sa part du risque du portefeuille. "
            "Un actif volatil ou très corrélé aux autres pèse plus dans le risque que dans le capital.",
            f"<b>{hot}</b> représente {pct(rc.loc[hot, 'Poids'], 0)} du capital mais "
            f"<b>{pct(rc.loc[hot, 'Part du risque'], 0)}</b> du risque. Volatilité du portefeuille : "
            f"{pct(rc['Contribution'].sum())} (= somme des contributions).",
        )

# --------------------------------------------------------------------------- #
with tabs[4]:
    alt = "ledoit_wolf" if params.cov_method == "sample" else "sample"
    res_alt = compute.split_for(params, bundle.prices, ppy, cov_method=alt)
    by_method = {params.cov_method: res, alt: res_alt}
    lw, sp = by_method["ledoit_wolf"], by_method["sample"]
    with st.container(border=True):
        section("Covariance de Ledoit-Wolf", "Σ̂ = (1 − δ)·S + δ·F : rétrécissement de la covariance empirique S vers une cible F")
        kpi_row([
            KPI("Coefficient de rétrécissement", lw.est.shrinkage, fmt="{:.3f}", icon="🛡️",
                help="Part de la cible structurée dans l'estimateur : 0 = covariance empirique pure."),
            KPI("Sharpe max · test (empirique)", sp.metrics_test.loc[MAX_SHARPE, "Sharpe"], fmt="{:.2f}", icon="📊"),
            KPI("Sharpe max · test (Ledoit-Wolf)", lw.metrics_test.loc[MAX_SHARPE, "Sharpe"], fmt="{:.2f}", icon="🧪"),
        ])
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        which = st.radio("Portefeuille", [MAX_SHARPE, MIN_VAR], horizontal=True, key="lw_cmp")
        cmp_df = pd.DataFrame({"Covariance empirique": sp.portfolios[which].weights,
                               "Ledoit-Wolf": lw.portfolios[which].weights})
        st.plotly_chart(grouped_bars(cmp_df, 320, colors=["#22D3EE", "#A855F7"], y_title="Poids"),
                        width="stretch", config=PLOTLY_CONFIG)
        cols = ["Rendement annualisé", "Volatilité annualisée", "Sharpe", "Drawdown maximal"]
        tab = pd.concat({"Empirique": sp.metrics_test.loc[[MIN_VAR, MAX_SHARPE], cols],
                         "Ledoit-Wolf": lw.metrics_test.loc[[MIN_VAR, MAX_SHARPE], cols]})
        st.markdown("**Performances hors échantillon (période de test)**")
        st.dataframe(format_metrics(tab), width="stretch")
        d_sh = lw.metrics_test.loc[MAX_SHARPE, "Sharpe"] - sp.metrics_test.loc[MAX_SHARPE, "Sharpe"]
        moved = (lw.portfolios[which].weights - sp.portfolios[which].weights).abs().sum() / 2
        explain(
            "Ledoit-Wolf « tire » la covariance estimée vers une structure simple, ce qui atténue les erreurs "
            "d'estimation que l'optimiseur a tendance à exploiter. On compare les poids, puis les performances "
            "sur la période de test.",
            f"Avec δ = {num(lw.est.shrinkage, 3)}, {pct(moved, 1)} du portefeuille « {which} » change de main. "
            f"Hors échantillon, le Sharpe maximal passe de {num(sp.metrics_test.loc[MAX_SHARPE, 'Sharpe'])} à "
            f"{num(lw.metrics_test.loc[MAX_SHARPE, 'Sharpe'])} ({num(d_sh, 2, signed=True)}). "
            + (f"Avec {num(lw.est.n_obs, 0)} observations pour {len(lw.est.mu)} actifs, la covariance empirique est "
               "déjà précise : le rétrécissement reste faible. Il devient utile quand la fenêtre d'estimation est "
               "courte ou les actifs nombreux (voir le test rétrospectif en fenêtre glissante)."
               if lw.est.shrinkage < 0.05 else
               ("Le rétrécissement améliore le résultat hors échantillon." if d_sh > 0
                else "Le rétrécissement n'améliore pas le résultat sur cette période.")),
        )
