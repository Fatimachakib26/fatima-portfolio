"""
Significativité statistique des différences de performance.

- Test de Jobson-Korkie corrigé par Memmel (2003) : H0 « SR_A = SR_B ».
    z = (SR_A − SR_B) / √{ [2(1−ρ) + ½(SR_A² + SR_B² − 2·SR_A·SR_B·ρ²)] / T }
  avec SR les ratios de Sharpe PÉRIODIQUES des rendements en excès du taux sans
  risque, ρ la corrélation des deux séries et T le nombre d'observations.
- Intervalle de confiance du Sharpe par bootstrap (rééchantillonnage avec
  remise des rendements, graine fixe → reproductible).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def memmel_test(r_a: pd.Series, r_b: pd.Series, rf_periodic: float) -> dict[str, float]:
    df = pd.concat([r_a, r_b], axis=1).dropna()
    a, b = df.iloc[:, 0] - rf_periodic, df.iloc[:, 1] - rf_periodic
    t = len(df)
    sr_a, sr_b = a.mean() / a.std(ddof=1), b.mean() / b.std(ddof=1)
    rho = float(np.corrcoef(a, b)[0, 1])
    var = (2 * (1 - rho) + 0.5 * (sr_a**2 + sr_b**2 - 2 * sr_a * sr_b * rho**2)) / t
    if var > 1e-18:
        z = (sr_a - sr_b) / np.sqrt(var)
    else:  # séries identiques (ρ = 1, même Sharpe) : aucune différence à tester
        z = 0.0 if abs(sr_a - sr_b) < 1e-12 else np.nan
    return {"sr_a": float(sr_a), "sr_b": float(sr_b), "rho": rho, "T": t,
            "z": float(z), "p_value": float(2 * (1 - norm.cdf(abs(z)))) if np.isfinite(z) else np.nan}


def bootstrap_sharpe_ci(r: pd.Series, rf_periodic: float, periods_per_year: int = 252,
                        n_boot: int = 1000, level: float = 0.95, seed: int = 42) -> tuple[float, float]:
    x = (r.dropna() - rf_periodic).to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    samples = x[idx]
    sr = samples.mean(axis=1) / samples.std(axis=1, ddof=1) * np.sqrt(periods_per_year)
    alpha = (1 - level) / 2
    lo, hi = np.quantile(sr, [alpha, 1 - alpha])
    return float(lo), float(hi)
