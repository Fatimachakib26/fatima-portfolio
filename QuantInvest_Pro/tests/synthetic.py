"""Données synthétiques à graine fixe, réservées aux tests (jamais affichées)."""
import numpy as np
import pandas as pd

ASSETS = ["A", "B", "C", "D", "E", "F"]


def synthetic_returns(n_days: int = 1500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    mu = np.array([0.0006, 0.0004, 0.0009, 0.0003, 0.0005, 0.0007])
    vol = np.array([0.018, 0.015, 0.030, 0.020, 0.017, 0.025])
    corr = 0.4 * np.ones((6, 6)) + 0.6 * np.eye(6)
    cov = corr * np.outer(vol, vol)
    r = rng.multivariate_normal(mu, cov, size=n_days)
    return pd.DataFrame(r, index=pd.bdate_range("2018-01-01", periods=n_days), columns=ASSETS)
