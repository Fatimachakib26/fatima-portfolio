"""Page 4 — Test rétrospectif.

Problématique : « Les portefeuilles optimisés par Markowitz font-ils mieux qu'un
portefeuille équipondéré, une fois testés sur une période différente de celle
de l'estimation ? Quelles méthodes rendent l'optimisation plus robuste ? »
"""
import numpy as np
import pandas as pd
import streamlit as st

from components import compute
from components.charts import (PLOTLY_CONFIG, announced_vs_realized_chart, drawdown_chart, realized_frontier_chart,
                               sensitivity_heatmap, stacked_weights_chart, wealth_chart)
from components.data_service import MarketBundle, render_data_alerts
from components.explain import explain, section
from components.formatting import METRIC_HELP, format_metrics, num, pct
from components.kpi_cards import KPI, banner, empty_state, kpi_row
from components.navbar import render_navbar
from components.state import get_market, get_params
from config import CRISES, REBALANCING, SENSITIVITY_WINDOWS, AppParams
from core.backtest import realized_forward_sharpe
from core.optimization import EQUAL, MAX_SHARPE, MIN_VAR
from core.reporting import returns_long, summary_long, to_csv_bytes, weights_long
from core.returns import periodic_rf, simple_returns
from core.stats_tests import bootstrap_sharpe_ci, memmel_test

params: AppParams = get_params()
bundle: MarketBundle = get_market()
render_navbar("Test rétrospectif", "Les portefeuilles optimisés résistent-ils à des données qu'ils n'ont jamais vues ?")
render_data_alerts(bundle)
if not bundle.ok:
    empty_state("Aucune donnée exploitable", "Cliquez sur Actualiser ou modifiez la sélection d'actifs.", "📡")
    st.stop()

ppy, rf = bundle.periods_per_year, params.risk_free_rate
try:
    res = compute.split_for(params, bundle.prices, ppy)
except ValueError as exc:
    banner(str(exc), "error", "⛔")
    st.stop()

tabs = st.tabs(["✂️ Hors échantillon simple", "🎯 Frontière estimée vs réalisée", "🔁 Fenêtre glissante",
                "🧪 Significativité", "🗺️ Sensibilité", "⬇️ Export Power BI"])

# --------------------------------------------------------------------------- #
# 1. Séparation simple
# --------------------------------------------------------------------------- #
with tabs[0]:
    t0, t1 = res.returns_test.index[0], res.returns_test.index[-1]
    st.caption(f"Estimation : {res.est.start:%d/%m/%Y} → {res.est.end:%d/%m/%Y} ({num(res.est.n_obs, 0)} obs.) · "
               f"Test : {t0:%d/%m/%Y} → {t1:%d/%m/%Y} ({num(len(res.returns_test), 0)} obs.) · poids estimés une fois, "
               f"puis figés · plafond {pct(params.weight_max, 0)} · date de séparation modifiable dans Paramètres")
    cols = ["Rendement annualisé", "Volatilité annualisée", "Sharpe", "Drawdown maximal", "Rendement cumulé"]
    with st.container(border=True):
        section("Estimation contre test", "Mêmes poids, deux périodes : ce que l'optimiseur voyait, puis la réalité")
        fmt = pd.concat({"Estimation": format_metrics(res.metrics_est[cols]),
                         "Test": format_metrics(res.metrics_test[cols])}, axis=1)
        fmt.columns = [f"{a} · {b}" for a, b in fmt.columns]
        st.dataframe(fmt, width="stretch")
        drop = res.metrics_est["Sharpe"] - res.metrics_test["Sharpe"]
        winner = res.metrics_test["Sharpe"].idxmax()
        explain(
            "Pour chaque portefeuille, la partie gauche reprend les indicateurs sur la période où les poids ont été "
            "calculés, la partie droite sur la période de test, jamais vue par l'optimiseur.",
            f"Le Sharpe maximal perd <b>{num(drop[MAX_SHARPE])}</b> point de Sharpe entre estimation et test "
            f"({num(res.metrics_est.loc[MAX_SHARPE, 'Sharpe'])} → {num(res.metrics_test.loc[MAX_SHARPE, 'Sharpe'])}), "
            f"le 1/N seulement {num(drop[EQUAL])}. Hors échantillon, le meilleur Sharpe revient à <b>{winner}</b> "
            f"({num(res.metrics_test.loc[winner, 'Sharpe'])}). L'optimiseur surestime ce qu'il optimise : c'est "
            f"l'« erreur de maximisation » de l'estimation.",
        )
    with st.container(border=True):
        section("Valeur de 100 investis sur la période de test", "Poids figés à la date de séparation, sans frais")
        bench = None
        if bundle.benchmark:
            b = simple_returns(bundle.benchmark_prices).loc[t0:t1]
            bench = b.rename(bundle.benchmark)
        st.plotly_chart(wealth_chart(res.returns_test, bench, 420), width="stretch", config=PLOTLY_CONFIG)
        final = 100 * (1 + res.returns_test).prod()
        explain(
            "Chaque courbe montre ce que seraient devenus 100 investis le premier jour de la période de test, "
            "avec les poids décidés à la date de séparation.",
            "Valeur finale : " + " ; ".join(f"{k} <b>{num(v, 1)}</b>" for k, v in final.items())
            + (f" ; {bundle.benchmark} {num(100 * (1 + bench).prod(), 1)}" if bench is not None else "") + ".",
        )

# --------------------------------------------------------------------------- #
# 2. Frontière estimée vs réalisée
# --------------------------------------------------------------------------- #
with tabs[1]:
    with st.spinner("Calcul des 30 portefeuilles de la frontière…"):
        fr = compute.realized(bundle.prices, params.split_date, rf, params.weight_min, params.weight_max,
                              params.cov_method, ppy)
    r_est = simple_returns(bundle.prices).loc[:pd.Timestamp(params.split_date)]
    r_test = simple_returns(bundle.prices).loc[res.returns_test.index]
    eq_w = np.full(len(bundle.assets), 1 / len(bundle.assets))
    eq_est = ((r_est @ eq_w).mean() * ppy, (r_est @ eq_w).std() * np.sqrt(ppy))
    eq_real = ((r_test @ eq_w).mean() * ppy, (r_test @ eq_w).std() * np.sqrt(ppy))
    with st.container(border=True):
        section("Frontière estimée vs frontière réalisée",
                "Chaque flèche relie un portefeuille de la frontière (estimé) à sa position réellement obtenue (test)")
        st.plotly_chart(realized_frontier_chart(fr, eq_est, eq_real, 520), width="stretch", config=PLOTLY_CONFIG)
        eq_sr_real = (eq_real[0] - rf) / eq_real[1]
        beat = int((fr["sharpe_realise"] > eq_sr_real).sum())
        ret_gap = (fr["rendement"] - fr["rendement_realise"]).mean()
        best_i = fr["sharpe_realise"].idxmax()
        explain(
            "La courbe violette est la frontière telle que l'optimiseur la voyait sur la période d'estimation ; "
            "la courbe cyan montre où ces mêmes portefeuilles (mêmes poids) ont réellement atterri sur la période "
            "de test. Le carré orange suit le 1/N.",
            f"En moyenne, les portefeuilles de la frontière réalisent <b>{pct(ret_gap, 1)}</b> de rendement annuel "
            f"de moins que prévu. Seuls <b>{beat} sur {len(fr)}</b> battent le 1/N en Sharpe réalisé "
            f"({num(eq_sr_real)}). Le meilleur réalisé est le n° {best_i + 1} (Sharpe {num(fr.loc[best_i, 'sharpe_realise'])}, "
            f"volatilité estimée {pct(fr.loc[best_i, 'volatilite'], 1)}) : "
            + ("les portefeuilles les moins risqués de la frontière ont le mieux résisté."
               if best_i < len(fr) / 3 else "le haut de la frontière a le mieux résisté sur cette période."),
        )

# --------------------------------------------------------------------------- #
# 3. Fenêtre glissante
# --------------------------------------------------------------------------- #
with tabs[2]:
    try:
        with st.spinner("Backtest en fenêtre glissante…"):
            bt = compute.rolling(bundle.daily_prices, rf, params.estimation_window, params.rebalance_days,
                                 params.transaction_cost_bps, params.weight_max)
    except ValueError as exc:
        banner(str(exc), "error", "⛔")
        st.stop()
    summ = bt.summary(rf)
    for name, n_fail in bt.failures.items():
        if n_fail:
            banner(f"<b>{name}</b> : {n_fail} décision(s) sans convergence de l'optimiseur.", "warn", "⚠️")
    st.caption(f"Début commun : {bt.start:%d/%m/%Y} (après la plus longue fenêtre testée, {max(SENSITIVITY_WINDOWS)} "
               f"séances) · fenêtre d'estimation {bt.window} séances · rééquilibrage "
               f"{REBALANCING.get(bt.step, f'{bt.step} séances').lower()} · frais {num(bt.cost_bps, 0)} pb × rotation")
    eq_name = next(c for c in bt.returns if c.startswith("Équipondéré"))
    best = summ["Sharpe"].idxmax()
    kpi_row([
        KPI("Meilleur Sharpe", summ.loc[best, "Sharpe"], fmt="{:.2f}", icon="🏆", foot=best),
        KPI("Sharpe du 1/N", summ.loc[eq_name, "Sharpe"], fmt="{:.2f}", icon="⚖️", foot="référence naïve"),
        KPI("Rotation la plus élevée", summ["Rotation annuelle"].max(), fmt="{:.0%}", icon="🔄",
            foot=summ["Rotation annuelle"].idxmax(), help=METRIC_HELP["Rotation annuelle"]),
        KPI("Écart annoncé − réalisé", (summ["Sharpe annoncé (moyen)"] - summ["Sharpe"]).max(), fmt="{:.2f}",
            icon="🎭", foot="pire stratégie", help=METRIC_HELP["Sharpe annoncé (moyen)"]),
    ])
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        section("Valeur de 100 investis", "Rendements nets de frais · zones grisées : crises")
        bench = None
        if bundle.benchmark:
            bench = simple_returns(bundle.clean.prices[bundle.benchmark]).loc[bt.returns.index[1]:].rename(bundle.benchmark)
        st.plotly_chart(wealth_chart(bt.returns, bench, 440, CRISES), width="stretch", config=PLOTLY_CONFIG)
        st.plotly_chart(drawdown_chart(bt.returns, 260), width="stretch", config=PLOTLY_CONFIG)
        final = 100 * (1 + bt.returns).prod()
        explain(
            "En haut, la valeur de 100 investis pour chaque stratégie, réoptimisée à chaque rééquilibrage avec les "
            "seules données passées. En bas, la baisse depuis le plus haut (drawdown).",
            f"<b>{best}</b> obtient le meilleur Sharpe ({num(summ.loc[best, 'Sharpe'])}) et termine à "
            f"{num(final[best], 1)}. Le 1/N termine à {num(final[eq_name], 1)}. Pire drawdown : "
            f"<b>{summ['Drawdown maximal'].idxmin()}</b> ({pct(summ['Drawdown maximal'].min(), 1)}).",
        )
    with st.container(border=True):
        section("Synthèse des stratégies", "Survolez un en-tête pour sa définition")
        show = ["Rendement annualisé", "Volatilité annualisée", "Sharpe", "Sortino", "Drawdown maximal",
                "Rotation annuelle", "Nb effectif de titres", "Sharpe annoncé (moyen)"]
        st.dataframe(format_metrics(summ[show]), width="stretch",
                     column_config={c: st.column_config.TextColumn(c, help=METRIC_HELP.get(c)) for c in show})
        conc = summ["Nb effectif de titres"].idxmin()
        explain(
            "Rotation annuelle : part du portefeuille échangée par an (coût en frais). Nombre effectif de titres : "
            "diversification réelle (6 = parfaitement réparti). Sharpe annoncé : promesse moyenne de l'optimiseur.",
            f"<b>{conc}</b> est le plus concentré ({num(summ.loc[conc, 'Nb effectif de titres'], 1)} titres effectifs) "
            f"et échange {pct(summ.loc[conc, 'Rotation annuelle'], 0)} du portefeuille par an. Le 1/N ne tourne que "
            f"de {pct(summ.loc[eq_name, 'Rotation annuelle'], 0)} (retour aux poids égaux).",
        )
    c1, c2 = st.columns(2, gap="medium")
    opt_names = [s for s in bt.returns if s != eq_name]
    with c1, st.container(border=True):
        s_w = st.selectbox("Stratégie", list(bt.returns), index=2, key="w_strat")
        section("Évolution des poids", "Poids quotidiens après dérive des cours")
        st.plotly_chart(stacked_weights_chart(bt.weights[s_w], 340), width="stretch", config=PLOTLY_CONFIG)
        d = bt.decisions[s_w]
        explain("Chaque bande colorée est la part d'un actif ; les sauts correspondent aux rééquilibrages.",
                f"{s_w} : en moyenne {num(d['n_effectif'].mean(), 1)} titres effectifs ; actif le plus souvent "
                f"dominant : <b>{d[bundle.assets].idxmax(axis=1).mode().iloc[0]}</b>.")
    with c2, st.container(border=True):
        s_a = st.selectbox("Stratégie", opt_names, index=1, key="a_strat")
        section("Sharpe annoncé vs Sharpe réalisé", "Promesse à chaque décision vs résultat des 12 mois suivants")
        ann = bt.decisions[s_a]["sharpe_annonce"]
        real = realized_forward_sharpe(bt.returns[s_a], ann.index, rf)
        st.plotly_chart(announced_vs_realized_chart(ann, real, 340), width="stretch", config=PLOTLY_CONFIG)
        ok = real.dropna()
        explain("Violet : Sharpe que l'optimiseur attendait au moment de la décision (sur sa fenêtre passée). "
                "Cyan : Sharpe effectivement obtenu sur l'année suivante.",
                f"Annoncé en moyenne <b>{num(ann.mean())}</b>, réalisé <b>{num(ok.mean())}</b> "
                f"(corrélation annoncé/réalisé : {num(np.corrcoef(ann.loc[ok.index], ok)[0, 1]) if len(ok) > 2 else '—'}). "
                "Le passé récent est un mauvais prédicteur du Sharpe futur.")

# --------------------------------------------------------------------------- #
# 4. Significativité
# --------------------------------------------------------------------------- #
with tabs[3]:
    bt = compute.rolling(bundle.daily_prices, rf, params.estimation_window, params.rebalance_days,
                         params.transaction_cost_bps, params.weight_max)
    eq_name = next(c for c in bt.returns if c.startswith("Équipondéré"))
    rf_d = periodic_rf(rf, 252)
    rows = {}
    for s in bt.returns:
        lo, hi = bootstrap_sharpe_ci(bt.returns[s], rf_d)
        sr = (bt.returns[s] - rf_d).mean() / bt.returns[s].std() * np.sqrt(252)
        t = memmel_test(bt.returns[s], bt.returns[eq_name], rf_d) if s != eq_name else None
        rows[s] = {"Sharpe": sr, "IC 95 % bas": lo, "IC 95 % haut": hi,
                   "z (vs 1/N)": t["z"] if t else np.nan, "p-valeur": t["p_value"] if t else np.nan}
    sig = pd.DataFrame(rows).T
    disp = pd.DataFrame({
        "Sharpe": sig["Sharpe"].map(num),
        "IC 95 % (bootstrap)": [f"[{num(a)} ; {num(b)}]" for a, b in zip(sig["IC 95 % bas"], sig["IC 95 % haut"])],
        "z de Memmel (vs 1/N)": sig["z (vs 1/N)"].map(num),
        "p-valeur": sig["p-valeur"].map(lambda p: "—" if pd.isna(p) else num(p, 3)),
    }, index=sig.index)
    with st.container(border=True):
        section("La surperformance est-elle statistiquement significative ?",
                f"Test de Memmel (2003) sur {num(len(bt.returns), 0)} séances · bootstrap 1 000 tirages (graine 42)")
        st.dataframe(disp.style.apply(lambda col: [
            "color:#F43F5E;font-weight:700" if (col.name == "p-valeur" and not pd.isna(p) and p < 0.05) else ""
            for p in sig["p-valeur"]], axis=0), width="stretch")
        n_sig = int((sig["p-valeur"] < 0.05).sum())
        widest = (sig["IC 95 % haut"] - sig["IC 95 % bas"]).mean()
        explain(
            "H0 : « la stratégie a le même Sharpe que le 1/N ». z mesure l'écart en nombre d'écarts-types ; "
            "p < 0,05 (en rouge) permet de rejeter H0. L'intervalle de confiance montre l'incertitude sur le Sharpe "
            "lui-même.",
            f"<b>{n_sig} stratégie(s) sur {len(sig) - 1}</b> diffèrent significativement du 1/N. Les intervalles de "
            f"confiance ont une largeur moyenne de {num(widest)} point de Sharpe : avec quelques années de données, "
            "un écart de Sharpe de 0,2 ou 0,3 n'est pas distinguable du hasard. C'est la conclusion classique de "
            "DeMiguel, Garlappi et Uppal (2009).",
        )

# --------------------------------------------------------------------------- #
# 5. Sensibilité
# --------------------------------------------------------------------------- #
with tabs[4]:
    try:
        with st.spinner("20 backtests en cours (mis en cache ensuite)…"):
            grid, ref = compute.sensitivity(bundle.daily_prices, rf, params.rebalance_days, params.transaction_cost_bps)
    except ValueError as exc:
        banner(str(exc), "error", "⛔")
        st.stop()
    with st.container(border=True):
        section("Sharpe hors échantillon du Sharpe maximal selon la fenêtre et le plafond",
                "Tous les backtests démarrent à la même date · couleur centrée sur le 1/N")
        st.plotly_chart(sensitivity_heatmap(grid, ref, 400), width="stretch", config=PLOTLY_CONFIG)
        g = grid.astype(float)
        bw, bc = np.unravel_index(np.nanargmax(g.values), g.shape)
        n_beat = int((g > ref).sum().sum())
        explain(
            "Chaque case est un backtest complet du Sharpe maximal avec une fenêtre d'estimation (lignes) et un "
            "plafond de poids (colonnes). Cyan : mieux que le 1/N ; rouge : moins bien.",
            f"<b>{n_beat} configurations sur {g.notna().sum().sum()}</b> battent le 1/N (Sharpe {num(ref)}). "
            f"Meilleure : fenêtre {g.index[bw]} séances, plafond {round(g.columns[bc] * 100)} % "
            f"(Sharpe {num(g.values[bw, bc])}). En moyenne sur les fenêtres : plafond "
            f"{round(g.columns[0] * 100)} % → Sharpe {num(g.iloc[:, 0].mean())}, plafond "
            f"{round(g.columns[-1] * 100)} % → {num(g.iloc[:, -1].mean())}. "
            + ("Sur cette période, desserrer le plafond a payé : les actifs favoris de l'optimiseur ont continué "
               "de surperformer. Le plafond limite la casse si ce n'est plus le cas."
               if g.iloc[:, -1].mean() > g.iloc[:, 0].mean() else
               "Sur cette période, un plafond strict protège : il limite la concentration sur des estimations bruitées."),
        )

# --------------------------------------------------------------------------- #
# 6. Export
# --------------------------------------------------------------------------- #
with tabs[5]:
    bt = compute.rolling(bundle.daily_prices, rf, params.estimation_window, params.rebalance_days,
                         params.transaction_cost_bps, params.weight_max)
    with st.container(border=True):
        section("Export des résultats pour Power BI", "Format long (une observation par ligne), séparateur « ; », "
                "virgule décimale, UTF-8")
        summary = summary_long({"Séparation simple – estimation": res.metrics_est,
                                "Séparation simple – test": res.metrics_test,
                                "Fenêtre glissante": bt.summary(rf)})
        rets = pd.concat([returns_long(res.returns_test, "Séparation simple – test"),
                          returns_long(bt.returns, "Fenêtre glissante")], ignore_index=True)
        weights = weights_long(bt.weights, "Fenêtre glissante")
        c1, c2, c3 = st.columns(3)
        c1.download_button("⬇️ Synthèse des stratégies", to_csv_bytes(summary), "synthese_strategies.csv",
                           "text/csv", width="stretch")
        c2.download_button("⬇️ Rendements journaliers", to_csv_bytes(rets), "rendements_journaliers.csv",
                           "text/csv", width="stretch")
        c3.download_button("⬇️ Poids à chaque date", to_csv_bytes(weights), "poids_par_date.csv",
                           "text/csv", width="stretch")
        st.caption(f"{num(len(summary), 0)} lignes de synthèse · {num(len(rets), 0)} rendements · "
                   f"{num(len(weights), 0)} poids. Dans Power BI : Obtenir des données → Texte/CSV, puis relier les "
                   "tables sur les colonnes « strategie » et « date ».")
        st.dataframe(summary.head(12), width="stretch", hide_index=True)
