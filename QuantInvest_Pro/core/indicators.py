"""
Module unique de calcul des indicateurs, avec traçabilité complète.

    calculer_indicateurs(rendements, benchmark, rf, ...) -> dict[str, Resultat]

Chaque Resultat contient la valeur, la formule, les entrées et le calcul
détaillé. RECALCUL[cle](entrees) recalcule la valeur à partir des seules
entrées : les tests vérifient que le détail affiché redonne bien le chiffre.

Conventions (rendements périodiques r_t, N périodes par an, r_f périodique
= (1 + rf)^(1/N) − 1, excès e_t = r_t − r_f) : voir les définitions dans META.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd
from scipy.stats import norm

from core.returns import periodic_rf
from core.trace import SOURCE_YAHOO, Entree, Resultat, fr_num, fr_val

# --------------------------------------------------------------------------- #
# Métadonnées : nom, unité, définition, formule, lecture, limites
# --------------------------------------------------------------------------- #
META: dict[str, dict] = {
    "rendement_annualise": dict(
        nom="Rendement annualisé", unite="pct",
        definition="Taux de croissance annuel composé : le rendement constant par an qui donne le même résultat final.",
        formule=r"R_{ann} = (1 + R_{cum})^{N/T} - 1",
        lecture="Au-dessus du taux sans risque : la prise de risque a été rémunérée.",
        limites="Ne dit rien du chemin parcouru (volatilité, pertes intermédiaires)."),
    "rendement_cumule": dict(
        nom="Rendement cumulé", unite="pct",
        definition="Gain ou perte total sur toute la période.",
        formule=r"R_{cum} = \prod_{t=1}^{T}(1 + r_t) - 1",
        lecture="100 % = valeur doublée.", limites="Dépend de la durée : à comparer sur des périodes identiques."),
    "volatilite": dict(
        nom="Volatilité annualisée", unite="pct",
        definition="Écart-type des rendements ramené à l'année : l'amplitude habituelle des variations.",
        formule=r"\sigma_{ann} = \hat\sigma(r)\,\sqrt{N}",
        lecture="Actions : 15 à 25 % pour un indice, 30 à 50 % pour une valeur technologique isolée.",
        limites="Traite hausses et baisses de la même façon ; suppose des rendements stables dans le temps."),
    "sharpe": dict(
        nom="Ratio de Sharpe", unite="ratio",
        definition="Rendement en excès du taux sans risque par unité de volatilité.",
        formule=r"S = \frac{N\,\bar e}{\hat\sigma(r)\sqrt{N}} = \frac{\bar e}{\hat\sigma(r)}\sqrt{N}",
        lecture="< 0,5 faible · 0,5–1 correct · 1–2 très bon · > 2 exceptionnel (souvent non durable).",
        limites="Suppose des rendements à peu près normaux ; très incertain sur quelques années de données."),
    "sortino": dict(
        nom="Ratio de Sortino", unite="ratio",
        definition="Comme le Sharpe, mais seule la volatilité des baisses (sous le taux sans risque) est pénalisée.",
        formule=r"So = \frac{N\,\bar e}{\sqrt{N}\sqrt{\frac{1}{T}\sum_t \min(e_t,0)^2}}",
        lecture="Supérieur au Sharpe si les fortes variations sont surtout des hausses.",
        limites="Moins de points pour estimer le risque de baisse : plus instable que le Sharpe."),
    "calmar": dict(
        nom="Ratio de Calmar", unite="ratio",
        definition="Rendement annualisé divisé par la pire baisse subie.",
        formule=r"C = \frac{R_{ann}}{|DD_{max}|}",
        lecture="> 1 : chaque année rapporte plus que la pire perte.",
        limites="Repose sur un seul événement (le pire drawdown)."),
    "ratio_information": dict(
        nom="Ratio d'information", unite="ratio",
        definition="Surperformance moyenne par rapport à l'indice de référence, par unité d'écart de suivi.",
        formule=r"IR = \frac{N\,\overline{(r - r_b)}}{\hat\sigma(r - r_b)\sqrt{N}}",
        lecture="> 0,5 : surperformance régulière ; < 0 : sous-performance.",
        limites="Dépend entièrement du choix de l'indice de référence."),
    "treynor": dict(
        nom="Ratio de Treynor", unite="pct",
        definition="Rendement en excès par unité de risque de marché (bêta).",
        formule=r"T = \frac{N\,\bar e}{\beta}",
        lecture="Pertinent pour un portefeuille déjà diversifié : seul le risque de marché compte.",
        limites="Instable si le bêta est proche de 0."),
    "drawdown_max": dict(
        nom="Drawdown maximal", unite="pct",
        definition="Pire baisse depuis un plus haut : la perte maximale d'un investisseur entré au pire moment.",
        formule=r"DD_{max} = \min_t \left(\frac{V_t}{\max_{s \le t} V_s} - 1\right)",
        lecture="−20 % : marché baissier ; −50 % : krach sévère.", limites="Un seul événement ; dépend de la période."),
    "duree_drawdown": dict(
        nom="Durée du pire drawdown", unite="seances",
        definition="Nombre de séances entre le plus haut précédant la pire baisse et le retour à ce niveau "
                   "(ou la fin de la période si le niveau n'est pas retrouvé).",
        formule=r"D = t_{\text{reprise}} - t_{\text{pic}}",
        lecture="252 séances ≈ 1 an pour retrouver son capital.", limites="Tronquée si la reprise n'a pas encore eu lieu."),
    "var95_hist": dict(
        nom="VaR 95 % historique", unite="pct",
        definition="Perte sur une période qui n'a été dépassée que 5 % du temps (5e centile des rendements observés).",
        formule=r"VaR_{95} = -q_{5\%}(r)", lecture="2 % : on perd plus de 2 % environ une séance sur 20.",
        limites="Ne dit rien de l'ampleur des pertes au-delà (voir CVaR)."),
    "var99_hist": dict(
        nom="VaR 99 % historique", unite="pct",
        definition="Perte sur une période dépassée seulement 1 % du temps.",
        formule=r"VaR_{99} = -q_{1\%}(r)", lecture="Événement environ 2 à 3 fois par an en données quotidiennes.",
        limites="Peu d'observations dans la queue : estimation bruitée."),
    "var95_param": dict(
        nom="VaR 95 % paramétrique", unite="pct",
        definition="VaR calculée en supposant des rendements de loi normale (VaR.py du cours).",
        formule=r"VaR_{95}^{N} = -(\bar r + \hat\sigma\, z_{0{,}05}),\quad z_{0{,}05} = -1{,}645",
        lecture="À comparer à la VaR historique : si elle est plus faible, la loi normale sous-estime le risque.",
        limites="Les rendements réels ont des queues épaisses."),
    "var99_param": dict(
        nom="VaR 99 % paramétrique", unite="pct",
        definition="VaR à 99 % sous l'hypothèse de normalité.",
        formule=r"VaR_{99}^{N} = -(\bar r + \hat\sigma\, z_{0{,}01}),\quad z_{0{,}01} = -2{,}326",
        lecture="Souvent nettement inférieure à la VaR historique à 99 %.", limites="Hypothèse de normalité."),
    "cvar95": dict(
        nom="CVaR 95 %", unite="pct",
        definition="Perte moyenne les 5 % de périodes les plus mauvaises (Expected Shortfall).",
        formule=r"CVaR_{95} = -E\left[r \mid r \le q_{5\%}\right]",
        lecture="Toujours ≥ VaR ; mesure la gravité des pertes extrêmes.", limites="Peu d'observations."),
    "beta": dict(
        nom="Bêta", unite="ratio",
        definition="Sensibilité au marché : variation moyenne du portefeuille quand l'indice varie de 1 %.",
        formule=r"\beta = \frac{\mathrm{Cov}(r, r_b)}{\mathrm{Var}(r_b)}",
        lecture="1 : comme le marché ; > 1 : amplifie ; < 1 : amortit.", limites="Instable dans le temps."),
    "alpha_jensen": dict(
        nom="Alpha de Jensen", unite="pct",
        definition="Rendement annuel en excès non expliqué par l'exposition au marché (CAPM).",
        formule=r"\alpha = N\,\bar e - \beta\, N\,\bar e_b",
        lecture="> 0 : création de valeur au-delà du risque de marché.", limites="Suppose le CAPM valide."),
    "tracking_error": dict(
        nom="Écart de suivi (tracking error)", unite="pct",
        definition="Volatilité de l'écart de rendement avec l'indice de référence.",
        formule=r"TE = \hat\sigma(r - r_b)\sqrt{N}",
        lecture="< 2 % : proche de l'indice ; > 10 % : gestion très différente.", limites="Dépend de l'indice."),
    "correlation_spy": dict(
        nom="Corrélation avec l'indice", unite="ratio",
        definition="Corrélation linéaire des rendements avec ceux de l'indice de référence.",
        formule=r"\rho = \frac{\mathrm{Cov}(r, r_b)}{\hat\sigma(r)\,\hat\sigma(r_b)}",
        lecture="Proche de 1 : peu de diversification par rapport au marché.", limites="Mesure linéaire seulement."),
    "asymetrie": dict(
        nom="Asymétrie (skewness)", unite="ratio",
        definition="Dissymétrie de la distribution : négative si les fortes baisses dominent les fortes hausses.",
        formule=r"\gamma_1 = \frac{m_3}{m_2^{3/2}},\quad m_k = \frac{1}{T}\sum_t (r_t-\bar r)^k",
        lecture="0 pour une loi normale.", limites="Très sensible à quelques valeurs extrêmes."),
    "kurtosis": dict(
        nom="Excès de kurtosis", unite="ratio",
        definition="Épaisseur des queues de distribution par rapport à la loi normale.",
        formule=r"\gamma_2 = \frac{m_4}{m_2^{2}} - 3",
        lecture="0 : loi normale ; > 3 : queues épaisses, pertes extrêmes plus fréquentes que prévu.",
        limites="Très sensible à quelques valeurs extrêmes."),
    "nombre_effectif": dict(
        nom="Nombre effectif de titres", unite="nombre",
        definition="Nombre d'actifs « équivalents » réellement détenus.",
        formule=r"N_{eff} = \frac{1}{\sum_i w_i^2}",
        lecture="= nombre d'actifs pour le 1/N ; = 1 pour un seul actif.", limites="Ignore les corrélations."),
    "rotation": dict(
        nom="Rotation annuelle", unite="pct",
        definition="Part du portefeuille échangée chaque année lors des rééquilibrages.",
        formule=r"\text{Rotation} = \frac{\sum_k \sum_i |\Delta w_{i,k}|}{\text{années}}",
        lecture="100 % : tout le portefeuille est renouvelé une fois par an.", limites="Ignore la taille des ordres."),
}

ORDER = list(META)

# --------------------------------------------------------------------------- #
# Recalcul à partir des seules entrées (contrôle de cohérence)
# --------------------------------------------------------------------------- #
RECALCUL: dict[str, Callable[[dict], float]] = {
    "rendement_cumule": lambda e: e["produit"] - 1,
    "rendement_annualise": lambda e: (1 + e["cum"]) ** (e["N"] / e["T"]) - 1,
    "volatilite": lambda e: e["sd"] * np.sqrt(e["N"]),
    "sharpe": lambda e: e["ex_ann"] / e["vol"],
    "sortino": lambda e: e["ex_ann"] / e["down"],
    "calmar": lambda e: e["ann"] / abs(e["mdd"]),
    "ratio_information": lambda e: e["act_ann"] / e["te"],
    "treynor": lambda e: e["ex_ann"] / e["beta"],
    "drawdown_max": lambda e: e["creux"] / e["pic"] - 1,
    "duree_drawdown": lambda e: e["duree"],
    "var95_hist": lambda e: -e["q"],
    "var99_hist": lambda e: -e["q"],
    "var95_param": lambda e: -(e["m"] + e["sd"] * e["z"]),
    "var99_param": lambda e: -(e["m"] + e["sd"] * e["z"]),
    "cvar95": lambda e: -e["queue"],
    "beta": lambda e: e["cov"] / e["var_b"],
    "alpha_jensen": lambda e: e["ex_ann"] - e["beta"] * e["exb_ann"],
    "tracking_error": lambda e: e["sd_act"] * np.sqrt(e["N"]),
    "correlation_spy": lambda e: e["cov"] / (e["sd"] * e["sd_b"]),
    "asymetrie": lambda e: e["m3"] / e["m2"] ** 1.5,
    "kurtosis": lambda e: e["m4"] / e["m2"] ** 2 - 3,
    "nombre_effectif": lambda e: 1 / e["somme_w2"],
    "rotation": lambda e: e["rot_tot"] / e["annees"],
}


def recalculer(res: Resultat) -> float:
    return float(RECALCUL[res.cle]({e.cle: e.valeur for e in res.entrees}))


# --------------------------------------------------------------------------- #
# Calcul
# --------------------------------------------------------------------------- #
def _pct(x: float, d: int = 2) -> str:
    return fr_val(x, "pct", d)


def _n(x: float, d: int = 4) -> str:
    return fr_num(x, d)


def _drawdown_info(r: pd.Series) -> tuple[float, float, float, pd.Timestamp, pd.Timestamp, pd.Timestamp | None, int]:
    wealth = pd.concat([pd.Series([1.0], index=[r.index[0] - pd.Timedelta(days=1)]), (1 + r).cumprod()])
    peak = wealth.cummax()
    dd = wealth / peak - 1
    t_low = dd.idxmin()
    pic_val = float(peak.loc[t_low])
    t_peak = wealth.loc[:t_low][wealth.loc[:t_low] == pic_val].index[-1]
    after = wealth.loc[t_low:]
    rec = after[after >= pic_val]
    t_rec = rec.index[0] if len(rec) else None
    end_pos = wealth.index.get_loc(t_rec) if t_rec is not None else len(wealth) - 1
    duree = int(end_pos - wealth.index.get_loc(t_peak))
    return float(dd.min()), pic_val, float(wealth.loc[t_low]), t_peak, t_low, t_rec, duree


def calculer_indicateurs(
    rendements: pd.Series,
    benchmark: pd.Series | None,
    rf: float,
    periods_per_year: int = 252,
    poids: pd.Series | None = None,
    rotation_totale: float | None = None,
    source: str = SOURCE_YAHOO,
    sujet: str = "",
    nom_benchmark: str = "SPY",
) -> dict[str, Resultat]:
    """Tous les indicateurs disponibles pour une série de rendements périodiques.

    benchmark : rendements de l'indice aux mêmes dates (None → indicateurs relatifs omis).
    poids : poids du portefeuille (→ nombre effectif de titres).
    rotation_totale : somme des rotations sur la période (→ rotation annuelle).
    """
    r = rendements.dropna().astype(float)
    if not isinstance(r.index, pd.DatetimeIndex):  # série non datée : dates de séances fictives (affichage)
        r = pd.Series(r.to_numpy(), index=pd.bdate_range("2000-01-03", periods=len(r)), name=r.name)
        if benchmark is not None:
            benchmark = pd.Series(benchmark.dropna().to_numpy()[: len(r)], index=r.index[: len(benchmark.dropna())])
    if len(r) < 3:
        raise ValueError("Au moins 3 observations sont nécessaires pour calculer les indicateurs.")
    N, T = periods_per_year, len(r)
    rf_p = periodic_rf(rf, N)
    e = r - rf_p
    sd = float(r.std(ddof=1))
    m = float(r.mean())
    base = dict(source=source, debut=r.index[0], fin=r.index[-1], n_obs=T, sujet=sujet)
    data = r.rename("rendement").to_frame()
    out: dict[str, Resultat] = {}

    def add(cle, valeur, entrees, etapes, donnees=data):
        meta = META[cle]
        out[cle] = Resultat(cle=cle, nom=meta["nom"], valeur=float(valeur), unite=meta["unite"],
                            definition=meta["definition"], formule=meta["formule"], entrees=entrees,
                            etapes=etapes, lecture=meta["lecture"], limites=meta["limites"], donnees=donnees, **base)

    rf_line = f"Taux sans risque : {_pct(rf)} par an → {_pct(rf_p, 4)} par période, (1 + {_pct(rf)})^(1/{N}) − 1"

    # Rendements
    produit = float((1 + r).prod())
    cum = produit - 1
    add("rendement_cumule", cum, [Entree("Produit des (1 + rₜ)", produit, "ratio", "produit")],
        [f"Π(1 + rₜ) sur {fr_num(T, 0)} périodes = {_n(produit)}", f"R_cum = {_n(produit)} − 1 = {_pct(cum)}"])
    ann = (1 + cum) ** (N / T) - 1
    add("rendement_annualise", ann,
        [Entree("Rendement cumulé", cum, "pct", "cum"), Entree("Périodes par an N", N, "nombre", "N"),
         Entree("Nombre de périodes T", T, "nombre", "T")],
        [f"(1 + {_pct(cum)})^({N}/{T}) − 1", f"= {_n(1 + cum)}^{_n(N / T)} − 1 = {_pct(ann)}"])
    vol = sd * np.sqrt(N)
    add("volatilite", vol, [Entree("Écart-type périodique", sd, "pct", "sd"), Entree("Périodes par an N", N, "nombre", "N")],
        [f"Écart-type des {fr_num(T, 0)} rendements = {_pct(sd, 4)}", f"{_pct(sd, 4)} × √{N} = {_pct(vol)}"])

    # Sharpe, Sortino
    ex_ann = float(e.mean()) * N
    add("sharpe", ex_ann / vol, [Entree("Excès moyen annualisé N·ē", ex_ann, "pct", "ex_ann"),
                                  Entree("Volatilité annualisée", vol, "pct", "vol")],
        [rf_line, f"Excès moyen annualisé : {_pct(float(e.mean()), 4)} × {N} = {_pct(ex_ann)}",
         f"Sharpe = {_pct(ex_ann)} / {_pct(vol)} = {fr_num(ex_ann / vol)}"])
    down = float(np.sqrt(np.mean(np.minimum(e, 0.0) ** 2)) * np.sqrt(N))
    if down > 0:
        add("sortino", ex_ann / down, [Entree("Excès moyen annualisé N·ē", ex_ann, "pct", "ex_ann"),
                                        Entree("Écart-type de baisse annualisé", down, "pct", "down")],
            [rf_line, f"Écart-type de baisse : √(moyenne des min(eₜ, 0)²) × √{N} = {_pct(down)}",
             f"Sortino = {_pct(ex_ann)} / {_pct(down)} = {fr_num(ex_ann / down)}"])

    # Drawdown
    mdd, pic, creux, t_peak, t_low, t_rec, duree = _drawdown_info(r)
    dd_data = (1 + r).cumprod().rename("valeur").to_frame()
    add("drawdown_max", mdd, [Entree("Valeur au plus haut", pic, "ratio", "pic"),
                              Entree("Valeur au plus bas", creux, "ratio", "creux")],
        [f"Plus haut le {t_peak:%d/%m/%Y} (valeur {_n(pic)}), plus bas le {t_low:%d/%m/%Y} (valeur {_n(creux)})",
         f"DD = {_n(creux)} / {_n(pic)} − 1 = {_pct(mdd)}"], dd_data)
    add("duree_drawdown", duree, [Entree("Séances du pic à la reprise", duree, "seances", "duree")],
        [f"Pic : {t_peak:%d/%m/%Y} ; creux : {t_low:%d/%m/%Y} ; "
         + (f"reprise : {t_rec:%d/%m/%Y}" if t_rec is not None else "niveau non retrouvé à la fin de la période"),
         f"Durée = {fr_num(duree, 0)} séances"], dd_data)
    if mdd < 0:
        add("calmar", ann / abs(mdd), [Entree("Rendement annualisé", ann, "pct", "ann"),
                                        Entree("Drawdown maximal", mdd, "pct", "mdd")],
            [f"Calmar = {_pct(ann)} / |{_pct(mdd)}| = {fr_num(ann / abs(mdd))}"])

    # VaR / CVaR
    for cle, lvl in (("var95_hist", 0.05), ("var99_hist", 0.01)):
        q = float(np.quantile(r.to_numpy(), lvl))
        add(cle, -q, [Entree(f"{int(lvl * 100)}e centile des rendements", q, "pct", "q")],
            [f"Classement des {fr_num(T, 0)} rendements, {int(lvl * 100)} % le plus bas : q = {_pct(q)}",
             f"VaR = −q = {_pct(-q)}"])
    for cle, lvl in (("var95_param", 0.05), ("var99_param", 0.01)):
        z = float(norm.ppf(lvl))
        v = -(m + sd * z)
        add(cle, v, [Entree("Moyenne périodique", m, "pct", "m"), Entree("Écart-type périodique", sd, "pct", "sd"),
                     Entree(f"Quantile normal z_{lvl}", z, "ratio", "z")],
            [f"VaR = −({_pct(m, 4)} + {_pct(sd, 4)} × ({fr_num(z, 3)})) = {_pct(v)}"])
    q5 = float(np.quantile(r.to_numpy(), 0.05))
    tail = r[r <= q5]
    add("cvar95", -float(tail.mean()), [Entree("Moyenne des rendements ≤ 5e centile", float(tail.mean()), "pct", "queue")],
        [f"{fr_num(len(tail), 0)} périodes sous le 5e centile ({_pct(q5)}), moyenne {_pct(float(tail.mean()))}",
         f"CVaR = {_pct(-float(tail.mean()))}"], tail.rename("rendement").to_frame())

    # Moments
    dev = r - m
    m2, m3, m4 = float((dev**2).mean()), float((dev**3).mean()), float((dev**4).mean())
    add("asymetrie", m3 / m2**1.5, [Entree("Moment centré d'ordre 2", m2, "ratio", "m2"),
                                     Entree("Moment centré d'ordre 3", m3, "ratio", "m3")],
        [f"γ₁ = {m3:.3e} / ({m2:.3e})^1,5 = {fr_num(m3 / m2**1.5)}".replace(".", ",")])
    add("kurtosis", m4 / m2**2 - 3, [Entree("Moment centré d'ordre 2", m2, "ratio", "m2"),
                                      Entree("Moment centré d'ordre 4", m4, "ratio", "m4")],
        [f"γ₂ = {m4:.3e} / ({m2:.3e})² − 3 = {fr_num(m4 / m2**2 - 3)}".replace(".", ",")])

    # Indicateurs relatifs à l'indice de référence
    if benchmark is not None:
        df = pd.concat([r, benchmark.astype(float)], axis=1, join="inner").dropna()
        if len(df) >= 3:
            rp, rb = df.iloc[:, 0], df.iloc[:, 1]
            cov = float(np.cov(rp, rb, ddof=1)[0, 1])
            var_b = float(rb.var(ddof=1))
            sd_b = float(rb.std(ddof=1))
            sd_p = float(rp.std(ddof=1))
            beta = cov / var_b
            both = df.rename(columns={df.columns[0]: "portefeuille", df.columns[1]: nom_benchmark})
            add("beta", beta, [Entree(f"Cov(r, r_{nom_benchmark})", cov, "ratio", "cov"),
                               Entree(f"Var(r_{nom_benchmark})", var_b, "ratio", "var_b")],
                [f"β = {cov:.3e} / {var_b:.3e} = {fr_num(beta)}".replace(".", ",")], both)
            add("correlation_spy", cov / (sd_p * sd_b),
                [Entree("Covariance", cov, "ratio", "cov"), Entree("Écart-type du portefeuille", sd_p, "pct", "sd"),
                 Entree(f"Écart-type de {nom_benchmark}", sd_b, "pct", "sd_b")],
                [f"ρ = {cov:.3e} / ({_pct(sd_p, 4)} × {_pct(sd_b, 4)}) = {fr_num(cov / (sd_p * sd_b))}".replace("e-0", "e−0")],
                both)
            exp_ann = float((rp - rf_p).mean()) * N
            exb_ann = float((rb - rf_p).mean()) * N
            alpha = exp_ann - beta * exb_ann
            add("alpha_jensen", alpha, [Entree("Excès annualisé du portefeuille", exp_ann, "pct", "ex_ann"),
                                        Entree("Bêta", beta, "ratio", "beta"),
                                        Entree(f"Excès annualisé de {nom_benchmark}", exb_ann, "pct", "exb_ann")],
                [f"α = {_pct(exp_ann)} − {fr_num(beta)} × {_pct(exb_ann)} = {_pct(alpha)}"], both)
            if abs(beta) > 1e-6:
                add("treynor", exp_ann / beta, [Entree("Excès annualisé", exp_ann, "pct", "ex_ann"),
                                                Entree("Bêta", beta, "ratio", "beta")],
                    [f"Treynor = {_pct(exp_ann)} / {fr_num(beta)} = {_pct(exp_ann / beta)}"], both)
            act = rp - rb
            sd_act = float(act.std(ddof=1))
            te = sd_act * np.sqrt(N)
            add("tracking_error", te, [Entree("Écart-type de l'écart de rendement", sd_act, "pct", "sd_act"),
                                       Entree("Périodes par an N", N, "nombre", "N")],
                [f"σ(r − r_b) = {_pct(sd_act, 4)} ; TE = {_pct(sd_act, 4)} × √{N} = {_pct(te)}"], both)
            if te > 0:
                act_ann = float(act.mean()) * N
                add("ratio_information", act_ann / te, [Entree("Écart moyen annualisé", act_ann, "pct", "act_ann"),
                                                        Entree("Écart de suivi", te, "pct", "te")],
                    [f"IR = {_pct(act_ann)} / {_pct(te)} = {fr_num(act_ann / te)}"], both)

    if poids is not None and len(poids):
        w2 = float((poids.astype(float) ** 2).sum())
        add("nombre_effectif", 1 / w2, [Entree("Somme des poids au carré Σw²", w2, "ratio", "somme_w2")],
            [" + ".join(f"{_pct(w, 1)}²" for w in poids if w > 0.0005) + f" = {_n(w2)}",
             f"N_eff = 1 / {_n(w2)} = {fr_num(1 / w2)}"], poids.rename("poids").to_frame())
    if rotation_totale is not None:
        annees = T / N
        add("rotation", rotation_totale / annees, [Entree("Rotation totale", rotation_totale, "pct", "rot_tot"),
                                                   Entree("Durée en années", annees, "nombre", "annees")],
            [f"{_pct(rotation_totale, 1)} / {fr_num(annees)} ans = {_pct(rotation_totale / annees, 1)} par an"])
    return {k: out[k] for k in ORDER if k in out}


def tableau(resultats: dict[str, dict[str, Resultat]], cles: list[str] | None = None) -> pd.DataFrame:
    """{sujet: {cle: Resultat}} → DataFrame numérique (sujets × indicateurs, noms en français)."""
    cles = cles or ORDER
    return pd.DataFrame({s: {META[k]["nom"]: (res[k].valeur if k in res else np.nan) for k in cles}
                         for s, res in resultats.items()}).T


# --------------------------------------------------------------------------- #
# Indicateurs « annoncés » par l'optimiseur (ex ante)
# --------------------------------------------------------------------------- #
RECALCUL["sharpe_annonce"] = lambda e: (e["ret"] - e["rf"]) / e["vol"]
RECALCUL["ecart_sharpe"] = lambda e: e["annonce"] - e["realise"]


def sharpe_annonce(weights: pd.Series, mu: pd.Series, cov: pd.DataFrame, rf: float, debut, fin, n_obs: int,
                   source: str = SOURCE_YAHOO, sujet: str = "") -> Resultat:
    w = weights.to_numpy()
    ret = float(w @ mu[weights.index].to_numpy())
    vol = float(np.sqrt(w @ cov.loc[weights.index, weights.index].to_numpy() @ w))
    terms = " + ".join(f"{_pct(wi, 1)} × {_pct(mu[a], 1)}" for a, wi in weights.items() if wi > 0.0005)
    return Resultat(
        cle="sharpe_annonce", nom="Sharpe annoncé (ex ante)", valeur=(ret - rf) / vol, unite="ratio",
        definition="Sharpe promis par l'optimiseur, calculé avec μ et Σ estimés sur la période d'estimation.",
        formule=r"S^{ex\,ante} = \frac{w^\top\mu - r_f}{\sqrt{w^\top\Sigma w}}",
        entrees=[Entree("Rendement espéré wᵀμ", ret, "pct", "ret"), Entree("Taux sans risque", rf, "pct", "rf"),
                 Entree("Volatilité espérée √(wᵀΣw)", vol, "pct", "vol")],
        etapes=[f"wᵀμ = {terms} = {_pct(ret)}", f"√(wᵀΣw) = {_pct(vol)}",
                f"S = ({_pct(ret)} − {_pct(rf)}) / {_pct(vol)} = {fr_num((ret - rf) / vol)}"],
        source=source, debut=debut, fin=fin, n_obs=n_obs, sujet=sujet,
        lecture="À comparer au Sharpe réalisé sur la période de test.",
        limites="Repose sur des moyennes historiques ; l'optimiseur exploite leurs erreurs (erreur de maximisation).",
        donnees=pd.DataFrame({"poids": weights, "μ annualisé": mu[weights.index]}))


def ecart_sharpe(annonce: Resultat, realise: Resultat) -> Resultat:
    v = annonce.valeur - realise.valeur
    return Resultat(
        cle="ecart_sharpe", nom="Écart annoncé − réalisé", valeur=v, unite="ratio",
        definition="Différence entre le Sharpe promis sur la période d'estimation et le Sharpe obtenu en test.",
        formule=r"\Delta S = S^{ex\,ante} - S^{test}",
        entrees=[Entree("Sharpe annoncé", annonce.valeur, "ratio", "annonce"),
                 Entree("Sharpe réalisé (test)", realise.valeur, "ratio", "realise")],
        etapes=[annonce.etapes[-1], realise.etapes[-1], f"ΔS = {fr_num(annonce.valeur)} − {fr_num(realise.valeur)} = {fr_num(v)}"],
        source=realise.source, debut=realise.debut, fin=realise.fin, n_obs=realise.n_obs, sujet=realise.sujet,
        lecture="> 0 : l'optimiseur a surestimé sa performance.", limites="Une seule période de test.")
