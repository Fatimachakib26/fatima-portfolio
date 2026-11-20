"""Achat puis conservation, sensibilité à la fenêtre, crises, diversification."""
import numpy as np
import pandas as pd

from core.backtest import crisis_performance, realized_points, static_split, window_sensitivity
from core.diversification import analyse_universe, mean_pairwise_corr, volatility_at_return
from core.optimization import EQUAL, MAX_SHARPE
from core.portfolio import buy_and_hold_returns
from tests.synthetic import synthetic_returns

R = synthetic_returns()
RF = 0.03


def test_buy_and_hold_matches_manual_wealth():
    w = pd.Series([0.5, 0.3, 0.2, 0, 0, 0], index=R.columns)
    r = buy_and_hold_returns(R.iloc[:60], w)
    manual = ((1 + R.iloc[:60]).prod() * w).sum()             # valeur finale de 1 investi
    assert abs((1 + r).prod() - manual) < 1e-12


def test_buy_and_hold_weights_drift_while_constant_mix_does_not():
    w = pd.Series(1 / 6, index=R.columns)
    bh = buy_and_hold_returns(R, w)
    cm = R @ w
    assert abs(bh.iloc[0] - cm.iloc[0]) < 1e-15                # identiques le premier jour
    assert not np.allclose(bh.to_numpy(), cm.to_numpy())       # puis différents (dérive)


def test_static_split_test_period_is_buy_and_hold():
    s = static_split(R, R.index[999], RF, 0, 0.4)
    w = s.portfolios[MAX_SHARPE].weights
    expected = buy_and_hold_returns(R.iloc[1000:], w)
    pd.testing.assert_series_equal(s.returns_test[MAX_SHARPE], expected, check_names=False)


def test_window_sensitivity_ignores_post_split_data_for_weights():
    split = R.index[999]
    g1, _ = window_sensitivity(R, split, RF, [1, 2], [0.4, 1.0])
    assert g1.notna().all().all()
    # même période de test, passé modifié AVANT la fenêtre d'un an : la ligne « 1 an » ne change pas
    altered = R.copy()
    altered.iloc[:500] *= 3
    g2, _ = window_sensitivity(altered, split, RF, [1], [0.4, 1.0])
    pd.testing.assert_series_equal(g1.loc[1], g2.loc[1])


def test_window_sensitivity_skips_unavailable_history():
    g, _ = window_sensitivity(R, R.index[300], RF, [5], [0.4])
    assert g.isna().all().all()


def test_realized_points_announced_equals_optimizer():
    s = static_split(R, R.index[999], RF, 0, 0.4)
    pts = realized_points(R, R.index[999], s.portfolios, RF)
    assert abs(pts.loc[MAX_SHARPE, "sharpe"] - s.portfolios[MAX_SHARPE].sharpe) < 1e-12
    assert set(pts.index) == set(s.portfolios)


def test_crisis_performance():
    r = pd.Series(0.01, index=R.index)
    out = crisis_performance({"x": r}, [("test", str(R.index[10].date()), str(R.index[19].date()))])
    assert abs(out.loc[0, "Rendement cumulé"] - (1.01**10 - 1)) < 1e-12 and out.loc[0, "Drawdown maximal"] == 0


def test_diversification_weights_and_corr():
    u = analyse_universe(R, R.index[999], RF, 0, 0.4)
    assert abs(u.max_sharpe_weights.sum() - 1) < 1e-8 and u.max_sharpe_weights.max() <= 0.4 + 1e-8
    c = pd.DataFrame([[1, 0.5], [0.5, 1]])
    assert mean_pairwise_corr(c) == 0.5
    assert np.isnan(volatility_at_return(u.frontier, 10.0))
