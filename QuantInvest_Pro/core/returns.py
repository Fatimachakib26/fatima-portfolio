"""
Rendements et estimation des paramètres de Markowitz (μ, Σ).

Conventions :
- Rendements SIMPLES r_t = P_t / P_{t-1} − 1 : ils s'agrègent linéairement
  entre actifs (r_p = wᵀr), contrairement aux log-rendements du cours.
- Annualisation avec N périodes par an (252 en quotidien) :
  μ = N · moyenne,  Σ = N · Σ_périodique,  σ = √N · écart-type.
- Taux sans risque périodique : (1 + rf)^(1/N) − 1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.robust import estimate_cov


def simple_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Rendements simples ; la première date (sans rendement) est retirée."""
    return prices.pct_change(fill_method=None).iloc[1:]


def periodic_rf(rf_annual: float, periods_per_year: int = 252) -> float:
    return (1.0 + rf_annual) ** (1.0 / periods_per_year) - 1.0


@dataclass
class Estimates:
    """Paramètres annualisés estimés sur un échantillon de rendements."""

    mu: pd.Series             # rendements espérés annualisés
    cov: pd.DataFrame         # covariance annualisée
    corr: pd.DataFrame
    vol: pd.Series            # volatilités annualisées
    periods_per_year: int
    n_obs: int
    start: pd.Timestamp
    end: pd.Timestamp
    method: str               # "sample" ou "ledoit_wolf"
    shrinkage: float | None   # coefficient de rétrécissement (Ledoit-Wolf)


def estimate(returns: pd.DataFrame, periods_per_year: int = 252, method: str = "sample") -> Estimates:
    """Estime μ et Σ à partir de `returns` UNIQUEMENT (aucune donnée extérieure)."""
    if len(returns) < 2:
        raise ValueError("Au moins 2 observations sont nécessaires pour estimer Σ.")
    cov_p, shrink = estimate_cov(returns, method)
    cov = cov_p * periods_per_year
    vol = pd.Series(np.sqrt(np.diag(cov)), index=returns.columns)
    corr = cov / np.outer(vol, vol)
    return Estimates(
        mu=returns.mean() * periods_per_year,
        cov=cov,
        corr=corr,
        vol=vol,
        periods_per_year=periods_per_year,
        n_obs=len(returns),
        start=returns.index[0],
        end=returns.index[-1],
        method=method,
        shrinkage=shrink,
    )


def rolling_mean_correlation(returns: pd.DataFrame, window: int = 63) -> pd.Series:
    """Corrélation moyenne de toutes les paires d'actifs, sur fenêtre glissante.

    Valeur à la date t = moyenne des corrélations calculées sur les `window`
    dernières séances jusqu'à t (incluse) : aucune donnée future.
    """
    n = returns.shape[1]
    if n < 2:
        raise ValueError("Au moins 2 actifs sont nécessaires.")
    rc = returns.rolling(window).corr()
    arr = rc.to_numpy().reshape(len(returns), n, n)
    off_diag_sum = arr.sum(axis=(1, 2)) - n          # diagonale = 1
    out = pd.Series(off_diag_sum / (n * (n - 1)), index=returns.index, name="Corrélation moyenne")
    return out.dropna()
