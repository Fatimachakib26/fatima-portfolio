"""Page — Sources et méthodologie : origine des données, traitements, formules, hypothèses, journal."""
import pandas as pd
import streamlit as st

from components.data_service import MarketBundle, source_text
from components.explain import section
from components.kpi_cards import card_title
from components.navbar import render_navbar
from components.state import get_market, get_params
from config import AppParams, FFILL_LIMIT, MAX_MISSING_RATIO
from core.indicators import META

p: AppParams = get_params()
bundle: MarketBundle = get_market()
render_navbar("Sources et méthodologie", "D'où viennent les données, comment elles sont traitées, quelles formules")
tabs = st.tabs(["🗄️ Sources et traitements", "📐 Méthodologie", "∑ Formules des indicateurs", "⚖️ Hypothèses et références",
                "📚 Scripts du cours", "🧾 Journal des calculs"])

with tabs[0]:
    raw = bundle.raw
    with st.container(border=True):
        section("Source de chaque série", source_text(bundle))
        st.dataframe(pd.DataFrame({
            "Origine": {t: {"live": "Yahoo Finance (direct)", "cache": "Copie locale (Yahoo indisponible)",
                            "missing": "Indisponible"}[s_] for t, s_ in raw.source.items()},
            "Devise": {t: raw.currencies.get(t) or "—" for t in raw.source},
            "Téléchargé le": {t: raw.fetched_at[t].strftime("%d/%m/%Y %H:%M") if t in raw.fetched_at else "—" for t in raw.source},
        }), width="stretch")
        st.markdown("- **Bibliothèque** : `yfinance`, fonction `download(..., auto_adjust=True)` : cours de clôture "
                    "**ajustés** des dividendes et des divisions d'actions.\n"
                    "- **Fuseau horaire** : dates de séance normalisées sans heure ni fuseau (clôture de chaque marché).\n"
                    "- **Profil et fondamentaux** : `yfinance.Ticker.info`, lus le jour de la consultation (non historisés).")
    with st.container(border=True):
        section("Traitements appliqués, dans l'ordre")
        c = bundle.clean
        st.markdown(f"""
1. **Alignement des dates** : dates sans fuseau, triées, doublons supprimés.
2. **Prix invalides** (≤ 0 ou infinis) remplacés par des valeurs manquantes.
3. **Exclusion** d'un actif au-delà de {MAX_MISSING_RATIO:.0%} de valeurs manquantes.
4. **Report de la dernière valeur** limité à {FFILL_LIMIT} séances (jours fériés), jamais vers l'arrière.
5. **Historique commun** : seules les dates où tous les actifs ont un prix sont conservées
   ({c.start:%d/%m/%Y} → {c.end:%d/%m/%Y}, {len(c.prices):,} séances).
6. **Rendements simples** rₜ = Pₜ / Pₜ₋₁ − 1 ; **annualisation** : μ × 252, σ × √252 (52 en hebdomadaire, 12 en mensuel).
""".replace(",", "\u202f"))
# --------------------------------------------------------------------------- #
with tabs[1]:
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
with tabs[4], st.container(border=True):
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


with tabs[2]:
    groups = {"Rendement": ["rendement_annualise", "rendement_cumule"],
              "Performance ajustée du risque": ["sharpe", "sortino", "calmar", "ratio_information", "treynor"],
              "Risque": ["volatilite", "drawdown_max", "duree_drawdown", "var95_hist", "var99_hist", "var95_param",
                         "var99_param", "cvar95"],
              "Relation au marché": ["beta", "alpha_jensen", "tracking_error", "correlation_spy"],
              "Forme de la distribution": ["asymetrie", "kurtosis"], "Construction": ["nombre_effectif", "rotation"]}
    for g, keys in groups.items():
        with st.container(border=True):
            section(g)
            for k in keys:
                st.markdown(f"**{META[k]['nom']}** — {META[k]['definition']}")
                st.latex(META[k]["formule"])

with tabs[3]:
    with st.container(border=True):
        section("Hypothèses et limites")
        st.markdown("""
- **Dividendes** : réinvestis via les cours ajustés ; pas d'impôts ni de frais de garde.
- **Biais du survivant** : les 6 actions sont des gagnantes connues d'aujourd'hui ; leur choix utilise une information future.
- **Période unique** : une seule séparation estimation / test ; les conclusions dépendent de cette période.
- **Taux sans risque fixe** ({:.2%} par an), alors qu'il a fortement varié entre 2019 et 2026.
- **Normalité** : Markowitz, la VaR paramétrique et le Monte-Carlo supposent des rendements normaux ; les données montrent des queues épaisses.
- **Exécution** : au cours de clôture, actions fractionnables, frais proportionnels à la rotation.
""".format(p.risk_free_rate).replace(".", ",", 1))
    with st.container(border=True):
        section("Références")
        st.markdown("""
- Markowitz, H. (1952). *Portfolio Selection*. The Journal of Finance.
- Sharpe, W. F. (1966). *Mutual Fund Performance*. The Journal of Business.
- Sortino, F., Price, L. (1994). *Performance Measurement in a Downside Risk Framework*.
- Ledoit, O., Wolf, M. (2004). *Honey, I Shrunk the Sample Covariance Matrix*.
- Memmel, C. (2003). *Performance Hypothesis Testing with the Sharpe Ratio*. Finance Letters.
- DeMiguel, V., Garlappi, L., Uppal, R. (2009). *Optimal Versus Naive Diversification*. Review of Financial Studies.
""")

with tabs[5]:
    log = st.session_state.get("journal", [])
    with st.container(border=True):
        section("Journal des calculs de la session", f"{len(log)} calcul(s) lancé(s)")
        if log:
            st.dataframe(pd.DataFrame(log[::-1]), hide_index=True, width="stretch")
        else:
            st.info("Aucun calcul lancé pour l'instant dans cette session.")
