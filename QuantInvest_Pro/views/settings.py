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

render_navbar("Paramètres & méthodologie", "Hypothèses de calcul, contraintes et références")
p: AppParams = get_params()

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
        card_title("3. Mesures de performance et de risque")
        st.markdown(r"- **Sharpe** : $\dfrac{\bar e}{\hat\sigma}\sqrt N$, $e_t = r_t - r_f$ ; **Sortino** : "
                    r"$\dfrac{N\,\bar e}{\sqrt{N\cdot\overline{\min(e_t,0)^2}}}$ (écart-type de baisse sur tout l'échantillon).")
        st.markdown(r"- **Calmar** : rendement annualisé (TCAM) / |drawdown maximal|.")
        st.markdown(r"- **VaR 95 % historique** : $-q_{5\%}(r)$ ; **CVaR 95 %** : $-E[r \mid r \le q_{5\%}]$ ; "
                    r"**VaR paramétrique** : $-(\bar r + \hat\sigma\, z_{0,05})$.")
        st.markdown(r"- **Drawdown maximal** : $\min_t \left(\dfrac{V_t}{\max_{s\le t} V_s} - 1\right)$ ; "
                    r"**contribution au risque** : $RC_i = w_i(\Sigma w)_i/\sigma_p$, $\sum_i RC_i = \sigma_p$.")
    with m4, st.container(border=True):
        card_title("4. Validation sans biais d'anticipation")
        st.markdown("**Séparation simple** : μ et Σ estimés jusqu'à la date de séparation incluse, poids figés, "
                    "évalués sur la période suivante.")
        st.markdown("**Fenêtre glissante** : à la clôture de la séance $t$, estimation sur les séances "
                    "$[t-W+1,\\,t]$ uniquement ; les poids s'appliquent au rendement de $t+1$ et dérivent ensuite "
                    "avec les cours. Frais = points de base × $\\sum_i|\\Delta w_i|$, achat initial inclus.")
        st.markdown("Hypothèses : exécution à la clôture, actions fractionnables, pas d'impôt, dividendes "
                    "réinvestis via les cours ajustés. Test de Memmel (2003) pour comparer deux Sharpe ; "
                    "intervalle de confiance par bootstrap (1 000 tirages, graine 42).")

    with st.container(border=True):
        card_title("5. Contrôle de l'optimiseur", "Variance minimale sans bornes : formule exacte contre SLSQP")
        st.latex(r"w^* = \frac{\Sigma^{-1}\mathbf 1}{\mathbf 1^\top \Sigma^{-1}\mathbf 1}"
                 r"\qquad\text{(lagrangien de } \min w^\top\Sigma w \text{ s.c. } \mathbf 1^\top w = 1)")
        bundle = st.session_state.get("market")
        if bundle is not None and bundle.ok:
            from components import compute

            est = compute.estimates(bundle.prices, p.split_date, bundle.periods_per_year, p.cov_method)
            chk = compute.optimizer_check(est.cov)
            cmp = pd.DataFrame({"Formule analytique": chk["analytique"], "SLSQP (bornes −1 000 % / +1 000 %)":
                                chk["numerique"], "Écart": (chk["analytique"] - chk["numerique"]).abs()})
            st.dataframe(cmp.map(lambda v: f"{v:.6f}".replace(".", ",")), width="stretch")
            cls, icon = ("ok", "🟢") if chk["ok"] else ("ko", "🔴")
            st.markdown(f'<span class="qi-check {cls}">{icon} Écart maximal : {chk["ecart_max"]:.2e} '
                        f'(seuil 1e-04) — {"optimiseur validé" if chk["ok"] else "écart anormal"}</span>',
                        unsafe_allow_html=True)
            st.caption(f"Covariance estimée sur {est.start:%d/%m/%Y} → {est.end:%d/%m/%Y}. Les poids négatifs "
                       f"correspondent à des ventes à découvert, autorisées uniquement pour ce contrôle.")
        else:
            st.info("Chargez des données pour exécuter le contrôle.")

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
