"""Backtests : 1/N manuel, absence de biais d'anticipation, cohérence, vitesse."""
import time

import numpy as np
import pandas as pd

from core.backtest import Strategy, rolling_backtest, static_split
from core.optimization import EQUAL, MAX_SHARPE, max_sharpe
from core.returns import estimate, periodic_rf
from core.stats_tests import bootstrap_sharpe_ci, memmel_test
from core.verdict import build_verdict
from tests.synthetic import synthetic_returns

R = synthetic_returns()
RF = 0.03
STRATS = [Strategy("1/N", "equal"), Strategy("MV", "min_variance", cap=0.4),
          Strategy("MS", "max_sharpe"), Strategy("MS-LW", "max_sharpe", "ledoit_wolf", 0.4)]


def test_equal_weight_month_matches_manual_buy_and_hold():
    bt = rolling_backtest(R, [Strategy("1/N", "equal")], RF, window=252, step=21, cost_bps=0)
    d0 = bt.decisions["1/N"].index[3]                       # une décision quelconque
    i0 = R.index.get_loc(d0)
    month = R.iloc[i0 + 1: i0 + 22]                          # 21 séances jusqu'à la décision suivante
    manual = ((1 + month).prod() * (1 / 6)).sum() - 1        # achat 1/N, puis dérive des poids
    from_bt = (1 + bt.returns["1/N"].loc[month.index]).prod() - 1
    assert abs(manual - from_bt) < 1e-12


def test_weights_valid_at_every_decision():
    bt = rolling_backtest(R, STRATS, RF, 252, 21, 10)
    for s in STRATS:
        d = bt.decisions[s.name]
        w = d[list(R.columns)]
        np.testing.assert_allclose(w.sum(axis=1), 1, atol=1e-8)
        assert w.to_numpy().min() >= -1e-9 and w.to_numpy().max() <= max(s.cap, 1 / 6) + 1e-9
        assert d["converged"].all()


def test_no_look_ahead_future_changes_do_not_affect_past_weights():
    bt = rolling_backtest(R, STRATS, RF, 252, 21, 10)
    cut = bt.decisions["MS"].index[10]
    altered = R.copy()
    altered.loc[altered.index > cut] *= -3.0                 # futur complètement modifié
    bt2 = rolling_backtest(altered, STRATS, RF, 252, 21, 10)
    for s in STRATS:
        a = bt.decisions[s.name].loc[:cut]
        b = bt2.decisions[s.name].loc[:cut]
        pd.testing.assert_frame_equal(a, b)
        pd.testing.assert_series_equal(bt.returns[s.name].loc[:cut], bt2.returns[s.name].loc[:cut])


def test_backtest_max_sharpe_matches_optimisation_page_on_same_window():
    bt = rolling_backtest(R, [Strategy("MS", "max_sharpe", "sample", 1.0)], RF, 252, 21, 0)
    d = bt.decisions["MS"].index[5]
    i = R.index.get_loc(d)
    est = estimate(R.iloc[i - 251: i + 1], 252, "sample")  # même fenêtre : 252 séances jusqu'à d
    page = max_sharpe(est.mu, est.cov, RF, 0, 1.0).weights
    np.testing.assert_allclose(bt.decisions["MS"].loc[d, list(R.columns)].astype(float), page, atol=1e-8)


def test_transaction_costs_reduce_performance():
    a = rolling_backtest(R, [Strategy("MS", "max_sharpe")], RF, 252, 21, 0).returns["MS"]
    b = rolling_backtest(R, [Strategy("MS", "max_sharpe")], RF, 252, 21, 50).returns["MS"]
    assert (1 + b).prod() < (1 + a).prod()


def test_reproducible_and_fast():
    t = time.perf_counter()
    a = rolling_backtest(R, STRATS, RF, 252, 21, 10)
    assert time.perf_counter() - t < 10
    b = rolling_backtest(R, STRATS, RF, 252, 21, 10)
    pd.testing.assert_frame_equal(a.returns, b.returns)


def test_static_split_uses_only_estimation_period():
    s = static_split(R, R.index[999], RF, 0, 0.4)
    assert s.est.end == R.index[999] and s.returns_test.index[0] == R.index[1000]
    altered = R.copy()
    altered.iloc[1000:] *= 5
    s2 = static_split(altered, R.index[999], RF, 0, 0.4)
    pd.testing.assert_series_equal(s.portfolios[MAX_SHARPE].weights, s2.portfolios[MAX_SHARPE].weights)


def test_memmel_identical_series_and_symmetry():
    r = R["A"]
    t = memmel_test(r, r, 0.0)
    assert abs(t["z"]) < 1e-12 and abs(t["p_value"] - 1) < 1e-12
    ab, ba = memmel_test(R["A"], R["B"], 0.0), memmel_test(R["B"], R["A"], 0.0)
    assert abs(ab["z"] + ba["z"]) < 1e-12 and abs(ab["p_value"] - ba["p_value"]) < 1e-12


def test_memmel_formula():
    a, b = R["A"], R["C"]
    t = memmel_test(a, b, 0.0)
    sa, sb = a.mean() / a.std(), b.mean() / b.std()
    rho = np.corrcoef(a, b)[0, 1]
    var = (2 * (1 - rho) + 0.5 * (sa**2 + sb**2 - 2 * sa * sb * rho**2)) / len(a)
    assert abs(t["z"] - (sa - sb) / np.sqrt(var)) < 1e-12


def test_bootstrap_ci_reproducible_and_contains_point_estimate():
    r = R["A"]
    ci1, ci2 = bootstrap_sharpe_ci(r, 0.0), bootstrap_sharpe_ci(r, 0.0)
    assert ci1 == ci2
    point = r.mean() / r.std() * np.sqrt(252)
    assert ci1[0] < point < ci1[1]


def test_verdict_sentence_is_built_from_numbers():
    s = static_split(R, R.index[999], RF, 0, 0.4)
    v = build_verdict(s.returns_test, s.metrics_test, s.portfolios[MAX_SHARPE].sharpe, periodic_rf(RF),
                      s.returns_test.index[0], s.returns_test.index[-1])
    from core.verdict import fr_num
    assert fr_num(s.metrics_test.loc[EQUAL, "Sharpe"]) in v.sentence
    assert ("non significatif" in v.sentence) or ("pas statistiquement" in v.sentence) or v.significant
