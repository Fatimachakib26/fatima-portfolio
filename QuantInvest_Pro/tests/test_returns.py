"""Rendements, estimation de μ et Σ, corrélation glissante."""
import numpy as np
import pandas as pd

from core.returns import estimate, periodic_rf, rolling_mean_correlation, simple_returns
from tests.synthetic import synthetic_returns


def test_simple_returns():
    p = pd.Series([100.0, 110.0, 99.0])
    np.testing.assert_allclose(simple_returns(p).to_numpy(), [0.10, -0.10])


def test_annualisation():
    r = synthetic_returns()
    est = estimate(r, 252)
    np.testing.assert_allclose(est.mu, r.mean() * 252)
    np.testing.assert_allclose(est.cov, r.cov() * 252)
    np.testing.assert_allclose(est.vol, r.std() * np.sqrt(252))
    np.testing.assert_allclose(np.diag(est.corr), 1.0)


def test_periodic_rf_compounds_back():
    assert abs((1 + periodic_rf(0.04, 252)) ** 252 - 1.04) < 1e-12


def test_ledoit_wolf_shrinkage_in_unit_interval():
    est = estimate(synthetic_returns(), 252, "ledoit_wolf")
    assert 0 <= est.shrinkage <= 1
    assert np.all(np.linalg.eigvalsh(est.cov) > 0)


def test_rolling_mean_correlation_matches_direct_computation():
    r = synthetic_returns(300)
    rc = rolling_mean_correlation(r, 63)
    c = r.iloc[-63:].corr().to_numpy()
    expected = (c.sum() - 6) / 30
    assert abs(rc.iloc[-1] - expected) < 1e-10
    assert rc.index[0] == r.index[62]  # première valeur : fenêtre complète
