"""Analyses d'un portefeuille : attribution, rendements mensuels, sensibilité des poids."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.optimization import max_sharpe, min_variance


def drifted_weights(returns: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Poids en DÉBUT de chaque période pour un achat puis conservation."""
    growth = (1 + returns[weights.index]).cumprod() * weights
    start = growth.shift(1)
    start.iloc[0] = weights
    return start.div(start.sum(axis=1), axis=0)


def attribution(returns: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Contribution de chaque actif au rendement de chaque période : w_{i,t−1} × r_{i,t}
    (la somme sur les actifs redonne le rendement du portefeuille)."""
    return drifted_weights(returns, weights) * returns[weights.index]


def cumulative_attribution(returns: pd.DataFrame, weights: pd.Series) -> pd.DataFrame:
    """Contribution cumulée de chaque actif à la valeur du portefeuille (1 investi au départ) :
    Σ_s V_{s−1}·w_{i,s−1}·r_{i,s} ; la somme sur les actifs vaut V_t − 1."""
    port = (attribution(returns, weights)).sum(axis=1)
    v_prev = (1 + port).cumprod().shift(1).fillna(1.0)
    return attribution(returns, weights).mul(v_prev, axis=0).cumsum()


def monthly_table(r: pd.Series) -> pd.DataFrame:
    """Rendements mensuels composés : lignes = années, colonnes = mois (1 à 12) + « Année »."""
    m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
    tab = m.unstack()
    tab["Année"] = (1 + r).groupby(r.index.year).prod() - 1
    return tab


def weight_sensitivity(mu: pd.Series, cov: pd.DataFrame, rf: float, lo: float, hi: float, objective: str,
                       bump: float = 0.01) -> pd.DataFrame:
    """Variation des poids optimaux quand le rendement espéré d'UN actif change de ±bump.
    Lignes : actif dont μ est modifié (et sens) ; colonnes : variation du poids de chaque actif."""
    def solve(m):
        return (max_sharpe(m, cov, rf, lo, hi) if objective == "max_sharpe" else min_variance(m, cov, lo, hi, rf)).weights

    base = solve(mu)
    rows = {}
    for a in mu.index:
        for sign, lbl in ((1, "+"), (-1, "−")):
            m2 = mu.copy()
            m2[a] += sign * bump
            rows[f"μ {a} {lbl}{bump:.0%}".replace("%", " %")] = solve(m2) - base
    return pd.DataFrame(rows).T


def marginal_contributions(weights: pd.Series, mu: pd.Series, cov: pd.DataFrame, rf: float) -> pd.DataFrame:
    """Contribution marginale de chaque actif : ∂σ/∂wᵢ = (Σw)ᵢ/σ et ∂S/∂wᵢ = (μᵢ − r_f − S·(Σw)ᵢ/σ)/σ."""
    w = weights.to_numpy()
    S = cov.loc[weights.index, weights.index].to_numpy()
    m = mu[weights.index].to_numpy()
    sig = float(np.sqrt(w @ S @ w))
    sh = (w @ m - rf) / sig
    sw = S @ w
    return pd.DataFrame({"Poids": w, "μ annualisé": m, "∂σ/∂w (risque marginal)": sw / sig,
                         "∂Sharpe/∂w": (m - rf - sh * sw / sig) / sig}, index=weights.index)
