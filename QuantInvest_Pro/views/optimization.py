"""Page 2 — Optimisation de Markowitz (cœur mathématique).

Toutes les estimations portent sur la PÉRIODE D'ESTIMATION (début → date de
séparation) : la période de test est réservée à la validation.
"""
import pandas as pd
import streamlit as st

from components.state import get_market, get_params

from components import compute
from components.charts import (PLOTLY_CONFIG, corr_heatmap, donut_chart, frontier_chart, grouped_bars,
                               realized_frontier_chart, two_frontiers_chart)
from components.data_service import MarketBundle, render_data_alerts
from components.explain import explain, section
from components.formatting import format_metrics, num, pct, weights_table
from components.kpi_cards import KPI, banner, empty_state, kpi_row
from components.navbar import render_navbar
from config import COV_METHODS, FREQUENCIES, AppParams
import numpy as np
import plotly.graph_objects as go

from core import library as lib_mod
from core.backtest import realized_points
from core.optimization import optimize_custom, target_portfolio
from core.diversification import volatility_at_return
from core.preprocessing import DataQualityError, clean_prices, resample_prices
from core.returns import simple_returns
from core.portfolio import metrics_table as metrics_table_fn
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
                "🧩 Contribution au risque", "🛡️ Ledoit-Wolf", "🌍 Diversification", "🎛️ Contraintes"])

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
        ev = st.dataframe(pd.DataFrame({
            "Rendement moyen annualisé": stats.iloc[:, 0].map(pct),
            "Volatilité annualisée": stats.iloc[:, 1].map(pct),
            "Sharpe individuel": stats.iloc[:, 2].map(num),
        }), width="stretch", on_select="rerun", selection_mode="single-row", key="opt_stats_sel")
        if ev.selection.rows:
            st.session_state["focus_asset"] = stats.index[ev.selection.rows[0]]
            st.switch_page("views/asset_analysis.py")
        st.caption("Cliquez sur une ligne pour ouvrir la fiche de l'actif.")
        best, worst = stats.index[0], stats.index[-1]
        explain(
            "Chaque ligne résume un actif sur la période d'estimation : son rendement moyen, son risque "
            "(volatilité) et leur rapport (Sharpe, net du taux sans risque).",
            f"<b>{best}</b> a le meilleur couple rendement / risque (Sharpe {num(stats.iloc[0, 2])}), "
            f"<b>{worst}</b> le moins bon ({num(stats.iloc[-1, 2])}). L'optimiseur va naturellement favoriser "
            f"les premiers — si ces moyennes historiques se répètent.",
        )
    with c2, st.container(border=True):
        section("Matrice des corrélations", "Carte de chaleur des corrélations des rendements")
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
        d1.download_button("⬇️ Pondérations (CSV)", to_csv_bytes(w_export.rename_axis("actif").reset_index()),
                           "allocations_markowitz.csv", "text/csv", width="stretch")
        d2.download_button("⬇️ Pondérations (Excel)", to_excel_bytes({"Allocations": w_export, "Synthese": summary}),
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
            " (estimation). Le tableau ci-dessous dit si cette diversification forcée paie hors échantillon.",
        )
        perf_cols = ["Rendement annualisé", "Volatilité annualisée", "Sharpe", "Drawdown maximal", "Rendement cumulé"]
        cap_tab = pd.DataFrame({
            f"{k} · plafond {pct(cap, 0)}": res.metrics_test.loc[k, perf_cols] for k in (MIN_VAR, MAX_SHARPE)
        } | {f"{k} · sans plafond": res_free.metrics_test.loc[k, perf_cols] for k in (MIN_VAR, MAX_SHARPE)}).T
        cap_tab = cap_tab.loc[[f"{MIN_VAR} · plafond {pct(cap, 0)}", f"{MIN_VAR} · sans plafond",
                               f"{MAX_SHARPE} · plafond {pct(cap, 0)}", f"{MAX_SHARPE} · sans plafond"]]
        st.markdown(f"**Performance sur la période de test** ({res.returns_test.index[0]:%d/%m/%Y} – "
                    f"{res.returns_test.index[-1]:%d/%m/%Y}, achat puis conservation)")
        st.dataframe(format_metrics(cap_tab.astype(float)), width="stretch")
        d_ms = res.metrics_test.loc[MAX_SHARPE, "Sharpe"] - res_free.metrics_test.loc[MAX_SHARPE, "Sharpe"]
        d_dd = res.metrics_test.loc[MAX_SHARPE, "Drawdown maximal"] - res_free.metrics_test.loc[MAX_SHARPE, "Drawdown maximal"]
        explain(
            "Mêmes portefeuilles, avec et sans plafond, évalués sur la période de test que l'optimiseur n'a pas vue.",
            f"En test, le plafond change le Sharpe du Sharpe maximal de <b>{num(d_ms, 2, signed=True)}</b> et son "
            f"drawdown maximal de {num(100 * d_dd, 1, signed=True)} point(s) de pourcentage : "
            + ("la contrainte a payé hors échantillon." if d_ms > 0 else
               "sur cette période, la concentration sans plafond a mieux payé — au prix d'un risque concentré "
               f"sur {top}."),
        )

# --------------------------------------------------------------------------- #
with tabs[2]:
    with st.container(border=True):
        section("Frontière efficiente de Markowitz", "Portefeuilles admissibles, frontière exacte et portefeuilles remarquables")
        cl = compute.cloud(est.mu, est.cov, rf, params.n_simulations, params.weight_min, cap)
        fr = compute.frontier(est.mu, est.cov, rf, params.weight_min, cap)
        vmin, vmax = float(fr["volatilite"].min()), float(fr["volatilite"].max())
        tv = st.slider("Volatilité cible (%) — déplace le marqueur sur la frontière", round(vmin * 100, 1) + 0.1,
                       round(vmax * 100, 1), round((vmin + vmax) * 50, 1), 0.1, key="tv_slider") / 100
        tgt = target_portfolio(est.mu, est.cov, rf, params.weight_min, cap, target_vol=tv)
        fig_f = frontier_chart(cl, fr, ports, rf, 560, assets=pd.DataFrame({"rendement": est.mu, "volatilite": est.vol}))
        fig_f.add_trace(go.Scatter(x=[tgt.volatility], y=[tgt.expected_return], mode="markers", name="Cible",
                                   marker=dict(size=16, symbol="x", color="#F43F5E", line=dict(width=2)),
                                   hovertemplate="Cible<br>Rendement : %{y:.2%}<br>Volatilité : %{x:.2%}<extra></extra>"))
        ev_f = st.plotly_chart(fig_f, width="stretch", config=PLOTLY_CONFIG, on_select="rerun", selection_mode="points",
                               key="front_click")
        st.caption("Cliquez sur un point de la frontière ou du nuage pour voir ses poids, ou sur un actif pour ouvrir sa fiche.")
        picked, label = tgt.weights, f"Cible σ = {pct(tv, 1)}"
        pts = ev_f.selection.points if ev_f and ev_f.selection else []
        if pts:
            pt = pts[0]
            curve, idx = pt.get("curve_number"), pt.get("point_index")
            if curve == 0 and idx is not None:
                picked, label = cl.iloc[idx][list(est.mu.index)].astype(float), f"Portefeuille aléatoire n° {idx + 1}"
            elif curve == 1 and idx is not None:
                picked, label = fr.iloc[idx][list(est.mu.index)].astype(float), f"Frontière, point n° {idx + 1}"
            elif curve == 2 and idx is not None:
                st.session_state["focus_asset"] = est.mu.index[idx]
                st.switch_page("views/asset_analysis.py")
        p_ret = float(picked @ est.mu)
        p_vol = float(np.sqrt(picked @ est.cov @ picked))
        c_a, c_b = st.columns([2, 1])
        c_a.markdown(f"**{label}** — rendement espéré {pct(p_ret, 1)} · volatilité {pct(p_vol, 1)} · "
                     f"Sharpe {num((p_ret - rf) / p_vol)}")
        c_a.dataframe(picked.map(lambda v: pct(v, 1)).rename("Poids").to_frame().T, width="stretch")
        nm = c_b.text_input("Nom", value=label, key="front_name")
        if c_b.button("💾 Enregistrer dans la bibliothèque", key="front_save"):
            custom = st.session_state.setdefault("library_custom", {})
            from components.workspace import get_library
            if nm in get_library(params, bundle):
                banner(f"« {nm} » existe déjà.", "error", "⛔")
            else:
                custom[nm] = lib_mod.Entry(nm, {k: float(v) for k, v in picked.items()}, "frontiere",
                                           f"{label} (estimation)", lib_mod.next_color(get_library(params, bundle)),
                                           parametres=lib_mod.params_dict(est, rf, params.weight_min, cap, "frontiere"))
                st.toast(f"« {nm} » enregistré", icon="✅")
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

    with st.container(border=True):
        section("Frontière estimée contre frontière réalisée",
                f"30 portefeuilles estimés jusqu'au {params.split_date:%d/%m/%Y}, puis évalués avec les mêmes poids "
                "sur la période de test · flèches : position annoncée → position réalisée")
        with st.spinner("Calcul de la frontière réalisée…"):
            fr_real = compute.realized(bundle.prices, params.split_date, rf, params.weight_min, cap,
                                       params.cov_method, ppy)
            pts = realized_points(simple_returns(bundle.prices), params.split_date, ports, rf, ppy)
        st.plotly_chart(realized_frontier_chart(fr_real, pts, 520), width="stretch", config=PLOTLY_CONFIG)
        gap_ret = (fr_real["rendement"] - fr_real["rendement_realise"]).mean()
        explain(
            "Violet : la frontière telle que l'optimiseur la voyait. Cyan pointillé : où ces mêmes portefeuilles ont "
            "réellement atterri. Symboles creux : position annoncée ; pleins : position réalisée. Mêmes définitions "
            f"des deux côtés (moyenne × {ppy}, écart-type × √{ppy}, poids constants).",
            "Sharpe annoncé → réalisé : " + " ; ".join(
                f"<b>{k}</b> {num(r['sharpe'])} → {num(r['sharpe_realise'])} ({num(r['sharpe_realise'] - r['sharpe'], 2, signed=True)})"
                for k, r in pts.iterrows())
            + f". En moyenne, la frontière réalise {pct(gap_ret, 1)} de rendement annuel de moins que prévu.",
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

# --------------------------------------------------------------------------- #
with tabs[5]:
    EXTRA = {"TLT": "Obligations d'État américaines à long terme (ETF)", "GLD": "Or (ETF)"}
    with st.container(border=True):
        section("Test de diversification", "Que gagne-t-on en ajoutant des actifs non technologiques ?")
        st.markdown("Ajout de **TLT** (obligations d'État américaines à plus de 20 ans) et de **GLD** (or) aux "
                    f"{len(bundle.assets)} actions, avec les mêmes contraintes et la même période d'estimation.")
        if st.button("➕ Ajouter des actifs non technologiques (TLT, GLD)", key="add_diversif"):
            st.session_state["diversif_on"] = True
    if st.session_state.get("diversif_on"):
        extra_tickers = tuple(t for t in EXTRA if t not in bundle.assets)
        with st.spinner("Téléchargement de TLT et GLD…"):
            md = compute.extra_prices(extra_tickers, params.start_date, params.end_date)
        if md.failed:
            banner("Téléchargement impossible pour <b>" + ", ".join(md.failed) + "</b> : vérifiez la connexion puis "
                   "cliquez sur Actualiser.", "error", "⛔")
        else:
            try:
                combined = clean_prices(pd.concat([bundle.clean.prices[bundle.assets], md.prices], axis=1)).prices
                combined = resample_prices(combined, FREQUENCIES[params.frequency][0])
                u6 = compute.universe(combined[bundle.assets], params.split_date, rf, params.weight_min, cap,
                                      params.cov_method, ppy)
                u8 = compute.universe(combined, params.split_date, rf, params.weight_min, cap, params.cov_method, ppy)
            except (ValueError, DataQualityError) as exc:
                banner(f"Analyse impossible : {exc}", "error", "⛔")
                st.stop()
            n6, n8 = len(u6.assets), len(u8.assets)
            kpi_row([
                KPI("Corrélation moyenne", u8.mean_corr, fmt="{:.2f}", icon="🔗",
                    foot=f"{n8} actifs · contre {num(u6.mean_corr)} pour {n6}"),
                KPI("Sharpe maximal annoncé", u8.sharpe_announced, fmt="{:.2f}", icon="⭐",
                    foot=f"{n8} actifs · contre {num(u6.sharpe_announced)} pour {n6}"),
                KPI("Sharpe maximal en test", u8.sharpe_test, fmt="{:.2f}", icon="🧪",
                    foot=f"{n8} actifs · contre {num(u6.sharpe_test)} pour {n6}"),
            ])
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                section("Deux frontières efficientes", f"Estimation {u6.est.start:%m/%Y} – {u6.est.end:%m/%Y} · "
                        f"plafond {pct(cap, 0)}")
                st.plotly_chart(two_frontiers_chart(u6, u8, f"{n6} actions technologiques", f"{n8} actifs (+ TLT, GLD)", 500),
                                width="stretch", config=PLOTLY_CONFIG)
                target = float(u6.frontier["rendement"].min())
                v6, v8 = volatility_at_return(u6.frontier, target), volatility_at_return(u8.frontier, target)
                w8 = u8.max_sharpe_weights
                added_w = float(w8[[t for t in EXTRA if t in w8.index]].sum())
                gain = ("" if pd.isna(v8) else
                        f" Pour le même rendement espéré ({pct(target, 1)}), la volatilité passe de {pct(v6, 1)} à "
                        f"<b>{pct(v8, 1)}</b> ({num(100 * (v8 - v6), 1, signed=True)} points).")
                explain(
                    "La courbe cyan (8 actifs) se situe au-dessus et à gauche de la violette : pour chaque niveau de "
                    "risque, on peut viser plus de rendement. Les points orange sont les actifs ajoutés.",
                    f"La corrélation moyenne passe de {num(u6.mean_corr)} à <b>{num(u8.mean_corr)}</b>.{gain} "
                    f"Le Sharpe maximal place {pct(added_w, 0)} du capital dans TLT et GLD ; son Sharpe annoncé passe de "
                    f"{num(u6.sharpe_announced)} à {num(u8.sharpe_announced)}, et en test de {num(u6.sharpe_test)} "
                    f"à <b>{num(u8.sharpe_test)}</b>. La diversification réduit le risque à coup sûr ; le gain de "
                    "rendement ajusté du risque, lui, dépend de la période.",
                )
                st.dataframe(weights_table({f"Sharpe maximal · {n6} actifs": u6.max_sharpe_weights.reindex(u8.assets).fillna(0),
                                            f"Sharpe maximal · {n8} actifs": w8}), width="stretch")

# --------------------------------------------------------------------------- #
with tabs[6]:
    from core.fundamentals import get_profile, sector_fr
    from core.returns import estimate as _estimate

    @st.cache_data(ttl=6 * 3600, show_spinner=False)
    def _sector(t):
        return sector_fr(get_profile(t).get("sector"))

    with st.container(border=True):
        section("Panneau de contraintes", "Modifiez puis cliquez sur « Recalculer » : résultat avant / après côte à côte")
        c1, c2, c3, c4 = st.columns(4)
        objective = c1.radio("Objectif", ["Sharpe maximal", "Variance minimale"], key="cst_obj")
        estim = c2.selectbox("Estimateur", ["sample", "ledoit_wolf"], format_func=COV_METHODS.get, key="cst_est")
        years = c3.selectbox("Fenêtre d'estimation", [1, 2, 3, 5], index=3, format_func=lambda y: f"{y} an(s) avant la séparation",
                             key="cst_years")
        rf_new = c4.number_input("Taux sans risque (%)", -5.0, 25.0, rf * 100, 0.25, key="cst_rf") / 100
        g1, g2 = st.columns(2)
        gmin = g1.number_input("Poids minimum global (%)", 0.0, 50.0, params.weight_min * 100, 1.0, key="cst_gmin") / 100
        gmax = g2.number_input("Poids maximum global (%)", 1.0, 100.0, cap * 100, 1.0, key="cst_gmax") / 100
        sectors = {a: _sector(a) for a in bundle.assets}
        table = pd.DataFrame({"Secteur": sectors, "Minimum (%)": gmin * 100, "Maximum (%)": gmax * 100})
        edited = st.data_editor(table, width="stretch", key="cst_table", disabled=["Secteur"],
                                column_config={"Minimum (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1),
                                               "Maximum (%)": st.column_config.NumberColumn(min_value=0, max_value=100, step=1)})
        groups = {}
        for a, sct in sectors.items():
            groups.setdefault(sct, []).append(a)
        st.markdown("**Plafond par secteur (%)**")
        cols = st.columns(max(len(groups), 1))
        caps = {g: cols[i].number_input(g, 0.0, 100.0, 100.0, 5.0, key=f"cst_sec_{i}") / 100 for i, g in enumerate(groups)}
        go_btn = st.button("🔄 Recalculer", type="primary", key="cst_go")
    if go_btn:
        st.session_state["cst_last"] = True
    if st.session_state.get("cst_last"):
        split = pd.Timestamp(params.split_date)
        r_all = simple_returns(bundle.prices)
        window = r_all.loc[(r_all.index > split - pd.DateOffset(years=years)) & (r_all.index <= split)]  # [no look-ahead]
        try:
            est_new = _estimate(window, ppy, estim)
            after = optimize_custom(est_new.mu, est_new.cov, rf_new, "max_sharpe" if objective == "Sharpe maximal" else "min_variance",
                                    edited["Minimum (%)"] / 100, edited["Maximum (%)"] / 100, groups, caps)
        except ValueError as exc:
            banner(f"Contraintes impossibles : {exc}", "error", "⛔")
            st.stop()
        before = ports[MAX_SHARPE if objective == "Sharpe maximal" else MIN_VAR]
        if not after.converged:
            banner(after.message, "warn", "⚠️")
        test_r = r_all.loc[r_all.index > split]
        from core.portfolio import buy_and_hold_returns as _bh
        m_b = metrics_table_fn({"Avant": _bh(test_r, before.weights), "Après": _bh(test_r, after.weights)}, rf_new, ppy)
        c1, c2 = st.columns(2, gap="medium")
        with c1, st.container(border=True):
            section("Poids avant / après")
            st.plotly_chart(grouped_bars(pd.DataFrame({"Avant": before.weights, "Après": after.weights}), 320,
                                         colors=["#8E8FB5", "#A855F7"], y_title="Poids"), width="stretch", config=PLOTLY_CONFIG)
        with c2, st.container(border=True):
            section("Indicateurs avant / après")
            comp = pd.DataFrame({"Avant": [before.expected_return, before.volatility, before.sharpe,
                                           m_b.loc["Avant", "Sharpe"], m_b.loc["Avant", "Drawdown maximal"]],
                                 "Après": [after.expected_return, after.volatility, after.sharpe,
                                           m_b.loc["Après", "Sharpe"], m_b.loc["Après", "Drawdown maximal"]]},
                                index=["Rendement espéré", "Volatilité espérée", "Sharpe annoncé", "Sharpe en test",
                                       "Drawdown maximal en test"])
            st.dataframe(comp.apply(lambda col: [pct(v, 1) if i in (0, 1, 4) else num(v) for i, v in enumerate(col)]),
                         width="stretch")
        explain("« Avant » : le portefeuille calculé avec les paramètres de la page Paramètres. « Après » : avec vos "
                "contraintes, sur la fenêtre d'estimation choisie. Le Sharpe en test est mesuré après la date de séparation.",
                f"Sharpe annoncé {num(before.sharpe)} → {num(after.sharpe)} ; en test {num(m_b.loc['Avant', 'Sharpe'])} → "
                f"<b>{num(m_b.loc['Après', 'Sharpe'])}</b>. Une contrainte réduit toujours le Sharpe annoncé, mais peut "
                "améliorer le résultat hors échantillon.")
