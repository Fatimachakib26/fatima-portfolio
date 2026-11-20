"""Page 6 — Paramètres et méthodologie.

Formulaire unique : les paramètres ne sont enregistrés qu'à la validation,
après contrôle de cohérence (AppParams.validate). Toutes les autres pages
lisent st.session_state["params"].
"""
from dataclasses import replace
from datetime import date

import streamlit as st

from components.kpi_cards import banner, card_title
from components.navbar import render_navbar
from config import (ASSET_UNIVERSE, BENCHMARKS, COV_METHODS, FREQUENCIES,
                    OPTIMIZATION_OBJECTIVES, REBALANCING, AppParams)

render_navbar("Paramètres & méthodologie", "Hypothèses de calcul, contraintes et références")
p: AppParams = st.session_state["params"]

tab_params, tab_method, tab_course = st.tabs(["⚙️ Paramètres", "📐 Méthodologie", "📚 Références du cours"])

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
        start = d1.date_input("Début", p.start_date, min_value=date(2000, 1, 1), max_value=date.today())
        end = d2.date_input("Fin", p.end_date, min_value=date(2000, 1, 1), max_value=date.today())
        freq = st.selectbox("Fréquence des rendements", list(FREQUENCIES), index=list(FREQUENCIES).index(p.frequency),
                            help="Facteur d'annualisation : 252 (quotidien), 52 (hebdomadaire), 12 (mensuel).")
        rf = st.number_input("Taux sans risque annuel (%)", -5.0, 25.0, p.risk_free_rate * 100, 0.25,
                             help="Utilisé dans le ratio de Sharpe. Converti par période : (1+rf)^(1/N) − 1.")

    c3, c4 = st.columns(2, gap="medium")
    with c3, st.container(border=True):
        card_title("Optimisation")
        wmin, wmax = st.slider("Bornes des pondérations (%)", 0, 100,
                               (int(round(p.weight_min * 100)), int(round(p.weight_max * 100))),
                               help="0 % minimum = pas de vente à découvert. Ex. max 40 % pour imposer la diversification.")
        obj = st.selectbox("Portefeuille retenu par défaut", list(OPTIMIZATION_OBJECTIVES),
                           index=list(OPTIMIZATION_OBJECTIVES).index(p.objective), format_func=OPTIMIZATION_OBJECTIVES.get)
        cov = st.selectbox("Estimateur de covariance", list(COV_METHODS),
                           index=list(COV_METHODS).index(p.cov_method), format_func=COV_METHODS.get)
        nsim = st.slider("Portefeuilles simulés (nuage Monte-Carlo)", 1000, 20000, p.n_simulations, 1000)
    with c4, st.container(border=True):
        card_title("Backtesting")
        win = st.slider("Fenêtre d'estimation (jours de cotation)", 63, 756, p.estimation_window, 21)
        reb = st.selectbox("Rééquilibrage", list(REBALANCING), index=list(REBALANCING).index(p.rebalancing),
                           format_func=REBALANCING.get)
        tc = st.number_input("Frais de transaction (points de base)", 0.0, 200.0, p.transaction_cost_bps, 1.0,
                             help="Coût = bps / 10 000 × rotation Σ|Δw|. 10 bps = 0,10 %.")
        cap = st.number_input("Capital initial ($)", 100.0, 1e9, p.initial_capital, 1000.0)

    submitted = st.form_submit_button("💾 Enregistrer les paramètres", use_container_width=True)

if submitted:
    extra = [t.strip().upper() for t in custom.split(",") if t.strip()]
    tickers = list(dict.fromkeys(sel + extra))  # dédoublonnage en gardant l'ordre
    candidate = replace(
        p, tickers=tickers, benchmark=bench, start_date=start, end_date=end, frequency=freq,
        risk_free_rate=rf / 100, weight_min=wmin / 100, weight_max=wmax / 100, objective=obj,
        cov_method=cov, n_simulations=nsim, estimation_window=win, rebalancing=reb,
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

# --------------------------------------------------------------------------- #
with tab_method:
    m1, m2 = st.columns(2, gap="medium")
    with m1, st.container(border=True):
        card_title("1. Rendements")
        st.markdown(r"Rendement simple : $r_t = \dfrac{P_t}{P_{t-1}} - 1$, avec $P$ = cours ajusté (dividendes, splits).")
        st.markdown(r"Rendement du portefeuille : $r_{p,t} = \sum_i w_i\, r_{i,t} = w^\top r_t$. "
                    "Les rendements simples s'agrègent linéairement entre actifs ; les log-rendements non.")
        st.markdown(r"Annualisation ($N$ = 252, 52 ou 12) : $\mu = N\,\bar r$, $\;\Sigma = N\,\hat\Sigma$, $\;\sigma = \sqrt N\,\hat\sigma$.")
    with m2, st.container(border=True):
        card_title("2. Optimisation de Markowitz")
        st.latex(r"\min_{w}\; w^\top \Sigma w \quad \text{s.c.}\quad \mathbf 1^\top w = 1,\;\; w_{\min}\le w_i \le w_{\max}")
        st.latex(r"\max_{w}\; \frac{w^\top\mu - r_f}{\sqrt{w^\top\Sigma w}} \quad \text{(Sharpe maximal)}")
        st.markdown("Résolution numérique par SciPy SLSQP ; frontière exacte : variance minimale pour chaque rendement cible.")
    m3, m4 = st.columns(2, gap="medium")
    with m3, st.container(border=True):
        card_title("3. Mesures de risque")
        st.markdown(r"- **VaR historique** $_\alpha$ : quantile $1-\alpha$ de la distribution empirique des pertes.")
        st.markdown(r"- **Expected Shortfall** : $ES_\alpha = E[L \mid L \ge VaR_\alpha]$.")
        st.markdown(r"- **Max Drawdown** : $\min_t \left(\dfrac{V_t}{\max_{s\le t} V_s} - 1\right)$.")
    with m4, st.container(border=True):
        card_title("4. Backtesting sans biais d'anticipation")
        st.markdown("À chaque date de rééquilibrage $t$, μ et Σ sont estimés **uniquement** sur $[t-W,\\,t-1]$ ; "
                    "les nouveaux poids s'appliquent à partir de $t+1$. Entre deux rééquilibrages, les poids dérivent "
                    "avec les prix. Hypothèses : exécution à la clôture, actions fractionnables, pas d'impôt, "
                    "dividendes réinvestis via les cours ajustés.")

# --------------------------------------------------------------------------- #
with tab_course, st.container(border=True):
    card_title("Correspondance avec les scripts du cours", "Comment chaque fichier fourni est repris dans l'application")
    st.markdown("""
| Script du cours | Repris dans | Adaptation apportée |
|---|---|---|
| `MarkowitzModel.py` | `core/optimization.py`, page Optimisation | Ajout du taux sans risque dans le Sharpe, portefeuille de variance minimale, frontière exacte, bornes modifiables, graine aléatoire fixe, rendements simples pour l'agrégation |
| `NormalReturns.py` | Analyse des actifs / du risque | Histogramme Plotly + densité normale ajustée, skewness, kurtosis et test de normalité (Jarque-Bera) |
| `VaR.py` | `core/risk.py` | VaR paramétrique (gaussienne) à côté de la VaR **historique** demandée par le sujet |
| `VaRMonteCarlo.py` | `core/risk.py` | VaR Monte-Carlo avec graine fixe, appliquée au portefeuille |
| `CAPM.py` | Analyse des actifs | Bêta / alpha de chaque actif contre le benchmark |
| `GBM.py`, `WienerProcess.py`, `RandomWalk.py` | Méthodologie | Justification de l'hypothèse de marche aléatoire des prix (hors calculs du portefeuille) |
| `BlackScholes*.py`, `CouponBond.py`, `ZeroCouponBond.py`, `PresentValue.py`, `VasicekModel.py`, `OrnsteinUhlenbeckProcess.py` | — | Options, obligations et taux : hors du périmètre Markowitz du sujet |

**Corrections nécessaires par rapport aux scripts d'origine :**
`yfinance` ≥ 0.2.51 ajuste les cours par défaut et ne renvoie plus la colonne `Adj Close`
(les scripts `ticker['Adj Close']` échouent) ; `resample('M')` est obsolète dans pandas ≥ 2.2
(remplacé par `'ME'`) ; le Sharpe du cours omet le taux sans risque.
""")
