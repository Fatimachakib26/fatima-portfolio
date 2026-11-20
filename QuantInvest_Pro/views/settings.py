"""Page 6 — Paramètres et méthodologie.

Formulaire unique : les paramètres ne sont enregistrés qu'à la validation,
après contrôle de cohérence (AppParams.validate). Toutes les autres pages
lisent st.session_state["params"].
"""
from dataclasses import replace
from datetime import date

import pandas as pd
import streamlit as st

from components.state import get_market, get_params

from components.kpi_cards import banner, card_title
from components.navbar import render_navbar
from config import (ASSET_UNIVERSE, BENCHMARKS, COV_METHODS, FREQUENCIES,
                    OPTIMIZATION_OBJECTIVES, REBALANCING, AppParams)

render_navbar("Paramètres", "Actifs, période, contraintes et réglages des tests")
p: AppParams = get_params()

(tab_params,) = st.tabs(["⚙️ Paramètres"])
st.caption("La méthodologie, le contrôle de l'optimiseur et les références du cours sont dans la page « Sources et méthodologie ».")

# --------------------------------------------------------------------------- #
with tab_params, st.form("params_form", border=False):
    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        card_title("Univers d'investissement")
        known = [t for t in p.tickers if t in ASSET_UNIVERSE]
        custom_default = ", ".join(t for t in p.tickers if t not in ASSET_UNIVERSE)
        sel = st.multiselect("Actifs", list(ASSET_UNIVERSE), default=known,
                             format_func=lambda t: f"{t} — {ASSET_UNIVERSE[t]}")
        custom = st.text_input("Autres tickers Yahoo (séparés par des virgules)", custom_default,
                               placeholder="ex. MC.PA, IAM.CS, BTC-USD")
        bench = st.selectbox("Indice de référence", list(BENCHMARKS),
                             index=list(BENCHMARKS).index(p.benchmark), format_func=BENCHMARKS.get)
    with c2, st.container(border=True):
        card_title("Période & fréquence")
        d1, d2 = st.columns(2)
        start = d1.date_input("Début", p.start_date, min_value=date(2000, 1, 1), max_value=date.today(),
                              format="DD/MM/YYYY")
        end = d2.date_input("Fin", p.end_date, min_value=date(2000, 1, 1), max_value=date.today(),
                            format="DD/MM/YYYY")
        split = st.date_input("Fin de la période d'estimation (date de séparation)", p.split_date,
                              min_value=date(2000, 1, 1), max_value=date.today(), format="DD/MM/YYYY",
                              help="Les poids sont estimés jusqu'à cette date incluse, puis testés sans "
                                   "modification sur la période suivante (validation hors échantillon).")
        freq = st.selectbox("Fréquence des rendements", list(FREQUENCIES), index=list(FREQUENCIES).index(p.frequency),
                            help="Facteur d'annualisation : 252 (quotidien), 52 (hebdomadaire), 12 (mensuel).")
        rf = st.number_input("Taux sans risque annuel (%)", -5.0, 25.0, p.risk_free_rate * 100, 0.25,
                             help="Utilisé dans le ratio de Sharpe. Converti par période : (1+rf)^(1/N) − 1.")

    c3, c4 = st.columns(2, gap="medium")
    with c3, st.container(border=True):
        card_title("Optimisation")
        wmin, wmax = st.slider("Bornes des pondérations : minimum et plafond par actif (%)", 0, 100,
                               (int(round(p.weight_min * 100)), int(round(p.weight_max * 100))),
                               help="0 % minimum = pas de vente à découvert. Ex. max 40 % pour imposer la diversification.")
        obj = st.selectbox("Portefeuille retenu par défaut", list(OPTIMIZATION_OBJECTIVES),
                           index=list(OPTIMIZATION_OBJECTIVES).index(p.objective), format_func=OPTIMIZATION_OBJECTIVES.get)
        cov = st.selectbox("Estimateur de covariance", list(COV_METHODS),
                           index=list(COV_METHODS).index(p.cov_method), format_func=COV_METHODS.get)
        nsim = st.slider("Portefeuilles simulés (nuage Monte-Carlo)", 1000, 20000, p.n_simulations, 1000)
    with c4, st.container(border=True):
        card_title("Test rétrospectif")
        win = st.slider("Fenêtre d'estimation glissante (séances)", 63, 756, p.estimation_window, 21)
        reb = st.selectbox("Rééquilibrage", list(REBALANCING), index=list(REBALANCING).index(p.rebalance_days),
                           format_func=REBALANCING.get)
        tc = st.number_input("Frais de transaction (points de base)", 0.0, 200.0, p.transaction_cost_bps, 1.0,
                             help="Coût = bps / 10 000 × rotation Σ|Δw|. 10 bps = 0,10 %.")
        cap = st.number_input("Capital initial ($)", 100.0, 1e9, p.initial_capital, 1000.0)

    submitted = st.form_submit_button("💾 Enregistrer les paramètres", width="stretch")

if submitted:
    extra = [t.strip().upper() for t in custom.split(",") if t.strip()]
    tickers = list(dict.fromkeys(sel + extra))  # dédoublonnage en gardant l'ordre
    candidate = replace(
        p, tickers=tickers, benchmark=bench, start_date=start, end_date=end, frequency=freq,
        risk_free_rate=rf / 100, weight_min=wmin / 100, weight_max=wmax / 100, objective=obj,
        cov_method=cov, n_simulations=nsim, estimation_window=win, rebalance_days=reb, split_date=split,
        transaction_cost_bps=tc, initial_capital=cap,
    )
    errors = candidate.validate()
    if errors:
        with tab_params:
            for e in errors:
                banner(e, "error", "⛔")
    else:
        st.session_state["params"] = candidate
        st.toast("Paramètres enregistrés", icon="✅")
        st.rerun()

