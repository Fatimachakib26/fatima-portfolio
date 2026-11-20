"""Indicateurs de performance et de risque."""
import numpy as np
import pandas as pd

from core.portfolio import (effective_n, historical_cvar, historical_var, max_drawdown, parametric_var,
                            performance_metrics, risk_contributions)
from core.returns import estimate, periodic_rf
from tests.synthetic import synthetic_returns


def test_historical_var_and_cvar_on_known_series():
    r = pd.Series(np.arange(1, 101) / 1000 - 0.05)   # −4,9 % … +5,0 %
    assert abs(historical_var(r) - 0.04405) < 1e-12  # interpolation linéaire du 5e centile
    assert abs(historical_cvar(r) - 0.047) < 1e-12   # moyenne de −4,9 %…−4,5 %


def test_parametric_var_normal():
    r = pd.Series(np.random.default_rng(42).normal(0.0, 0.01, 200_000))
    assert abs(parametric_var(r) - 0.01645) < 2e-4


def test_max_drawdown():
    r = pd.Series([0.10, -0.50, 0.20])               # 1 → 1,1 → 0,55 → 0,66
    assert abs(max_drawdown(r) + 0.5) < 1e-12


def test_sortino_uses_full_sample_downside_deviation():
    r = pd.Series([0.02, -0.01, 0.03, -0.02])
    m = performance_metrics(r, 0.0, 252)
    downside = np.sqrt(np.mean(np.minimum(r, 0) ** 2)) * np.sqrt(252)
    assert abs(m["Sortino"] - r.mean() * 252 / downside) < 1e-12


def test_metrics_definitions():
    r = synthetic_returns()["A"]
    m = performance_metrics(r, 0.03, 252)
    rf_p = periodic_rf(0.03)
    assert abs(m["Sharpe"] - (r - rf_p).mean() / r.std() * np.sqrt(252)) < 1e-12
    assert abs(m["Rendement cumulé"] - ((1 + r).prod() - 1)) < 1e-12
    assert abs(m["Calmar"] - m["Rendement annualisé"] / abs(m["Drawdown maximal"])) < 1e-12


def test_risk_contributions_sum_to_portfolio_volatility():
    est = estimate(synthetic_returns(), 252)
    w = pd.Series([0.3, 0.1, 0.2, 0.15, 0.15, 0.1], index=est.mu.index)
    rc = risk_contributions(w, est.cov)
    sigma = float(np.sqrt(w @ est.cov @ w))
    assert abs(rc["Contribution"].sum() - sigma) < 1e-12
    assert abs(rc["Part du risque"].sum() - 1) < 1e-12


def test_effective_n():
    assert abs(effective_n(np.full(6, 1 / 6)) - 6) < 1e-12
    assert effective_n([1, 0, 0]) == 1


def test_capm_beta_equals_cov_over_var():
    from core.capm import capm
    r = synthetic_returns()
    out = capm(r["A"], r["B"], 0.0)
    expected = r["A"].cov(r["B"]) / r["B"].var()
    assert abs(out["beta"] - expected) < 1e-10
