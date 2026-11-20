"""Scénarios : tests de résistance historiques, choc hypothétique, Monte-Carlo."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import CRISES
from core.portfolio import max_drawdown


def stress_table(series: dict[str, pd.Series]) -> pd.DataFrame:
    """Krachs historiques, pire semaine et pire mois de chaque portefeuille."""
    rows = []
    for name, r in series.items():
        row = {"Portefeuille": name}
        for label, a, b in CRISES:
            seg = r.loc[a:b]
            row[label] = float((1 + seg).prod() - 1) if len(seg) > 3 else np.nan
        w = (1 + r).rolling(5).apply(np.prod, raw=True) - 1
        m = (1 + r).rolling(21).apply(np.prod, raw=True) - 1
        row["Pire semaine"], row["Date (semaine)"] = float(w.min()), w.idxmin()
        row["Pire mois"], row["Date (mois)"] = float(m.min()), m.idxmin()
        row["Drawdown maximal"] = max_drawdown(r)
        rows.append(row)
    return pd.DataFrame(rows).set_index("Portefeuille")


def shock_loss(beta: float, market_shock: float, vol: float, vol_shock: float, z: float = 1.645) -> dict:
    """Perte attendue = β × choc de marché ; perte au pire à 95 % sur la même journée
    = β × choc − z × σ_jour × (1 + choc de volatilité) (résidu de marché ignoré)."""
    expected = beta * market_shock
    sigma_d = vol / np.sqrt(252) * (1 + vol_shock)
    return {"perte_attendue": expected, "perte_95": expected - z * sigma_d, "sigma_jour": sigma_d}


def monte_carlo(mu_annual: float, sigma_annual: float, n_paths: int = 1000, horizon: int = 252,
                seed: int = 42, start: float = 100.0) -> tuple[pd.DataFrame, float]:
    """Trajectoires de valeur sur `horizon` séances, rendements quotidiens normaux de moyenne
    μ/252 et d'écart-type σ/√252 (généralisation de GBM.py du cours). Renvoie les percentiles
    5 %, 50 %, 95 % par séance et la probabilité de finir sous la valeur initiale."""
    rng = np.random.default_rng(seed)
    r = rng.normal(mu_annual / 252, sigma_annual / np.sqrt(252), size=(n_paths, horizon))
    paths = start * np.cumprod(1 + r, axis=1)
    pct = pd.DataFrame({"P5": np.percentile(paths, 5, axis=0), "P50": np.percentile(paths, 50, axis=0),
                        "P95": np.percentile(paths, 95, axis=0)}, index=np.arange(1, horizon + 1))
    return pct, float((paths[:, -1] < start).mean())
