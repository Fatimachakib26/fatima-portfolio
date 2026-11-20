"""
Statistiques d'un portefeuille : performance, risque, diversification.

Définitions (séries de rendements PÉRIODIQUES r_t, N périodes par an,
r_f périodique = (1 + rf)^(1/N) − 1, excès e_t = r_t − r_f) :
- Rendement cumulé     : Π(1 + r_t) − 1
- Rendement annualisé  : taux de croissance annuel composé (TCAM)
                         (1 + cumulé)^(N/T) − 1
- Volatilité annualisée: écart-type(r) · √N
- Sharpe               : moyenne(e) / écart-type(r) · √N
- Sortino (Sortino & Price, 1994) : moyenne(e)·N / écart-type de baisse,
  écart-type de baisse = √(moyenne(min(e_t, 0)²)) · √N — toutes les
  séances comptent, les séances au-dessus de r_f valant 0.
- Calmar               : rendement annualisé / |drawdown maximal|
- Drawdown maximal     : min_t (V_t / max_{s≤t} V_s − 1), V = valeur du portefeuille
- VaR historique 95 %  : −(5e centile des rendements)  — perte sur 1 période
- CVaR 95 %            : −moyenne des rendements ≤ 5e centile
- VaR paramétrique 95 %: −(moyenne + écart-type · z₀,₀₅), loi normale
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from core.returns import periodic_rf

CONFIDENCE = 0.95


def fixed_weight_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """r_p,t = wᵀ r_t : poids constants (rééquilibrage implicite à chaque période,
    sans frais), convention de Markowitz et de DeMiguel et al. (2009)."""
    return returns[weights.index] @ weights


def buy_and_hold_returns(returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Achat au premier jour aux poids w, puis conservation : les poids dérivent
    avec les cours (aucun rééquilibrage, aucun frais après l'achat).
    V_t = Σᵢ wᵢ Π_{s≤t}(1 + r_{i,s}) ; r_p,t = V_t / V_{t−1} − 1, avec V_0 = 1."""
    growth = (1 + returns[weights.index]).cumprod()
    value = growth @ weights
    prev = value.shift(1).fillna(float(weights.sum()))
    return (value / prev - 1).rename("buy_and_hold")


def max_drawdown(r: pd.Series) -> float:
    wealth = np.concatenate([[1.0], (1 + r).cumprod().to_numpy()])
    peak = np.maximum.accumulate(wealth)
    return float((wealth / peak - 1).min())


def drawdown_series(r: pd.Series) -> pd.Series:
    wealth = (1 + r).cumprod()
    peak = np.maximum(wealth.cummax(), 1.0)
    return wealth / peak - 1


def historical_var(r: pd.Series, level: float = CONFIDENCE) -> float:
    return float(-np.quantile(r.to_numpy(), 1 - level))


def historical_cvar(r: pd.Series, level: float = CONFIDENCE) -> float:
    q = np.quantile(r.to_numpy(), 1 - level)
    return float(-r[r <= q].mean())


def parametric_var(r: pd.Series, level: float = CONFIDENCE) -> float:
    return float(-(r.mean() + r.std(ddof=1) * norm.ppf(1 - level)))


def performance_metrics(r: pd.Series, rf_annual: float, periods_per_year: int = 252) -> dict[str, float]:
    r = r.dropna()
    n = len(r)
    rf_p = periodic_rf(rf_annual, periods_per_year)
    excess = r - rf_p
    std = r.std(ddof=1)
    cum = float((1 + r).prod() - 1)
    ann = (1 + cum) ** (periods_per_year / n) - 1
    downside = np.sqrt(np.mean(np.minimum(excess, 0.0) ** 2)) * np.sqrt(periods_per_year)
    mdd = max_drawdown(r)
    return {
        "Rendement annualisé": ann,
        "Volatilité annualisée": std * np.sqrt(periods_per_year),
        "Sharpe": excess.mean() / std * np.sqrt(periods_per_year) if std > 0 else np.nan,
        "Sortino": excess.mean() * periods_per_year / downside if downside > 0 else np.nan,
        "Calmar": ann / abs(mdd) if mdd < 0 else np.nan,
        "Drawdown maximal": mdd,
        "Rendement cumulé": cum,
        "VaR 95 % historique": historical_var(r),
        "CVaR 95 %": historical_cvar(r),
        "VaR 95 % paramétrique": parametric_var(r),
        "Observations": n,
    }


def metrics_table(series: dict[str, pd.Series], rf_annual: float, periods_per_year: int = 252) -> pd.DataFrame:
    """Une ligne par portefeuille, une colonne par indicateur."""
    return pd.DataFrame({k: performance_metrics(v, rf_annual, periods_per_year) for k, v in series.items()}).T


def risk_contributions(weights: pd.Series, cov: pd.DataFrame) -> pd.DataFrame:
    """Décomposition d'Euler de la volatilité : σ_p = Σᵢ RCᵢ,
    RCᵢ = wᵢ (Σw)ᵢ / σ_p ; part du risque = RCᵢ / σ_p (somme = 100 %)."""
    w = weights.to_numpy()
    S = cov.loc[weights.index, weights.index].to_numpy()
    sigma = float(np.sqrt(w @ S @ w))
    rc = w * (S @ w) / sigma
    return pd.DataFrame({"Poids": w, "Contribution": rc, "Part du risque": rc / sigma}, index=weights.index)


def effective_n(weights: pd.Series | np.ndarray) -> float:
    """Nombre effectif de titres : 1 / Σwᵢ² (= N pour le 1/N, = 1 si concentré)."""
    w = np.asarray(weights, dtype=float)
    return float(1.0 / np.sum(w**2))
