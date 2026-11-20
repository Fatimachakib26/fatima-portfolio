"""Optimiseur de Markowitz : contraintes, formule analytique, cohérence."""
import numpy as np
import pytest

from core.optimization import (check_optimizer, efficient_frontier, max_sharpe, min_variance,
                               min_variance_analytic, random_portfolios)
from core.returns import estimate
from tests.synthetic import synthetic_returns

EST = estimate(synthetic_returns(), 252)
RF = 0.03


@pytest.mark.parametrize("hi", [1.0, 0.4, 0.25])
def test_weights_sum_to_one_and_respect_bounds(hi):
    for res in (min_variance(EST.mu, EST.cov, 0, hi, RF), max_sharpe(EST.mu, EST.cov, RF, 0, hi)):
        w = res.weights
        assert res.converged
        assert abs(w.sum() - 1) < 1e-8
        assert w.min() >= -1e-9 and w.max() <= hi + 1e-9


def test_cap_binds_when_unconstrained_solution_is_concentrated():
    free = max_sharpe(EST.mu, EST.cov, RF, 0, 1.0)
    capped = max_sharpe(EST.mu, EST.cov, RF, 0, 0.25)
    assert free.weights.max() > 0.25 and capped.weights.max() <= 0.25 + 1e-9
    assert capped.sharpe <= free.sharpe + 1e-9  # une contrainte ne peut pas améliorer l'optimum


def test_numerical_min_variance_matches_closed_form():
    chk = check_optimizer(EST.cov)
    assert chk["ok"] and chk["ecart_max"] < 1e-4
    np.testing.assert_allclose(min_variance_analytic(EST.cov).sum(), 1.0)


def test_max_sharpe_beats_every_random_portfolio():
    best = max_sharpe(EST.mu, EST.cov, RF, 0, 1).sharpe
    cloud = random_portfolios(EST.mu, EST.cov, RF, 3000)
    assert cloud["sharpe"].max() <= best + 1e-9


def test_frontier_is_increasing_and_feasible():
    fr = efficient_frontier(EST.mu, EST.cov, RF, 0, 0.4, 20)
    assert fr["converged"].all()
    assert np.all(np.diff(fr["volatilite"]) >= -1e-8)
    w = fr[list(EST.mu.index)]
    np.testing.assert_allclose(w.sum(axis=1), 1, atol=1e-8)
    assert w.to_numpy().max() <= 0.4 + 1e-8


def test_infeasible_cap_is_rejected():
    with pytest.raises(ValueError):
        min_variance(EST.mu, EST.cov, 0, 0.1)  # 6 × 10 % < 100 %


def test_reproducible():
    a, b = random_portfolios(EST.mu, EST.cov, RF, 500), random_portfolios(EST.mu, EST.cov, RF, 500)
    assert a.equals(b)
