"""
Test de diversification : effet de l'ajout d'actifs peu corrélés (obligations,
or) sur la frontière efficiente et le Sharpe maximal. Estimation uniquement sur
la période d'estimation ; performance du Sharpe maximal mesurée ensuite en test.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.backtest import split_returns
from core.optimization import efficient_frontier, max_sharpe
from core.portfolio import buy_and_hold_returns, metrics_table
from core.returns import Estimates, estimate


@dataclass
class UniverseResult:
    assets: list[str]
    est: Estimates
    frontier: pd.DataFrame
    max_sharpe_weights: pd.Series
    sharpe_announced: float
    sharpe_test: float
    mean_corr: float


def mean_pairwise_corr(corr: pd.DataFrame) -> float:
    n = len(corr)
    return float((corr.to_numpy().sum() - n) / (n * (n - 1)))


def analyse_universe(returns: pd.DataFrame, split_date, rf: float, lo: float, hi: float,
                     cov_method: str = "sample", periods_per_year: int = 252) -> UniverseResult:
    r_est, r_test = split_returns(returns, split_date)
    est = estimate(r_est, periods_per_year, cov_method)       # [no look-ahead] ≤ date de séparation
    cap = max(hi, 1 / returns.shape[1])
    ms = max_sharpe(est.mu, est.cov, rf, lo, cap)
    test = metrics_table({"x": buy_and_hold_returns(r_test, ms.weights)}, rf, periods_per_year)
    return UniverseResult(list(returns.columns), est, efficient_frontier(est.mu, est.cov, rf, lo, cap, 30),
                          ms.weights, ms.sharpe, float(test.loc["x", "Sharpe"]), mean_pairwise_corr(est.corr))


def volatility_at_return(frontier: pd.DataFrame, target: float) -> float:
    """Volatilité de la frontière pour un rendement cible (interpolation linéaire)."""
    f = frontier.sort_values("rendement")
    if not f["rendement"].min() <= target <= f["rendement"].max():
        return np.nan
    return float(np.interp(target, f["rendement"], f["volatilite"]))
