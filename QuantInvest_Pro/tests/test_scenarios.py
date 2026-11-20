"""Scénarios, contraintes personnalisées, rapport."""
import numpy as np
import pandas as pd
import pytest

from core.optimization import max_sharpe, optimize_custom
from core.report import build_html
from core.returns import estimate
from core.scenarios import monte_carlo, shock_loss, stress_table
from tests.synthetic import synthetic_returns

R = synthetic_returns()
EST = estimate(R, 252)


def test_monte_carlo_reproducible_and_ordered():
    a, pa = monte_carlo(0.1, 0.2)
    b, pb = monte_carlo(0.1, 0.2)
    pd.testing.assert_frame_equal(a, b)
    assert pa == pb and (a["P5"] <= a["P50"]).all() and (a["P50"] <= a["P95"]).all()


def test_shock_loss():
    out = shock_loss(1.5, -0.10, 0.2, 0.0)
    assert abs(out["perte_attendue"] + 0.15) < 1e-12 and out["perte_95"] < out["perte_attendue"]


def test_stress_table_columns():
    t = stress_table({"x": pd.Series(0.001, index=pd.bdate_range("2019-01-01", "2023-12-31"))})
    assert {"Pire semaine", "Pire mois", "Krach Covid"} <= set(t.columns)


def test_custom_bounds_and_sector_caps_respected():
    lo = pd.Series(0.05, index=EST.mu.index)
    hi = pd.Series(0.5, index=EST.mu.index)
    res = optimize_custom(EST.mu, EST.cov, 0.03, "max_sharpe", lo, hi, {"G": ["C", "F"]}, {"G": 0.2})
    w = res.weights
    assert res.converged and abs(w.sum() - 1) < 1e-8 and (w >= 0.05 - 1e-8).all() and (w <= 0.5 + 1e-8).all()
    assert w[["C", "F"]].sum() <= 0.2 + 1e-6
    free = optimize_custom(EST.mu, EST.cov, 0.03, "max_sharpe", lo * 0, hi * 2)
    np.testing.assert_allclose(free.weights, max_sharpe(EST.mu, EST.cov, 0.03, 0, 1).weights, atol=1e-4)


def test_custom_infeasible_messages():
    lo = pd.Series(0.3, index=EST.mu.index)
    with pytest.raises(ValueError, match="minimums"):
        optimize_custom(EST.mu, EST.cov, 0.03, "min_variance", lo, lo + 0.1)


def test_report_html():
    import plotly.graph_objects as go
    h = build_html("Test", "ok", {"T": pd.DataFrame({"a": [1]})}, {"F": go.Figure()}, ["h"], ["s"])
    assert "<table" in h and "plotly" in h
