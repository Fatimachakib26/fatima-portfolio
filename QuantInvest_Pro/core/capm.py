"""
CAPM (repris de CAPM.py du cours, en rendements simples quotidiens) :
r_i − r_f = α + β (r_m − r_f) + ε,  β = Cov(r_i, r_m) / Var(r_m).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from core.returns import periodic_rf


def capm(asset: pd.Series, market: pd.Series, rf_annual: float, periods_per_year: int = 252) -> dict:
    df = pd.concat([asset, market], axis=1).dropna()
    rf = periodic_rf(rf_annual, periods_per_year)
    y, x = df.iloc[:, 0] - rf, df.iloc[:, 1] - rf
    reg = stats.linregress(x, y)
    return {"beta": float(reg.slope), "alpha_annuel": float(reg.intercept * periods_per_year),
            "r2": float(reg.rvalue**2), "p_alpha": float(_p_intercept(x, y, reg)), "n": len(df),
            "x": x, "y": y, "intercept": float(reg.intercept)}


def _p_intercept(x, y, reg) -> float:
    n = len(x)
    resid = y - (reg.intercept + reg.slope * x)
    s2 = (resid**2).sum() / (n - 2)
    se = np.sqrt(s2 * (1 / n + x.mean() ** 2 / ((x - x.mean()) ** 2).sum()))
    t = reg.intercept / se
    return 2 * (1 - stats.t.cdf(abs(t), n - 2))


def descriptive_stats(returns: pd.DataFrame, periods_per_year: int = 252) -> pd.DataFrame:
    rows = {}
    for c in returns:
        r = returns[c].dropna()
        rows[c] = {"Rendement moyen annualisé": r.mean() * periods_per_year,
                   "Volatilité annualisée": r.std() * np.sqrt(periods_per_year),
                   "Pire séance": r.min(), "Meilleure séance": r.max(),
                   "Asymétrie": float(stats.skew(r)), "Excès de kurtosis": float(stats.kurtosis(r)),
                   "p Jarque-Bera": float(stats.jarque_bera(r).pvalue)}
    return pd.DataFrame(rows).T
