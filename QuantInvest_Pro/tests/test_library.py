"""Bibliothèque : parité de risque, cible, constructeur, JSON, absence d'anticipation."""
import numpy as np
import pandas as pd
import pytest

from core import library as lib
from core.backtest import split_returns
from core.optimization import max_feasible_return, min_variance, risk_parity, target_portfolio
from core.portfolio import risk_contributions
from core.returns import estimate
from tests.synthetic import synthetic_returns

R = synthetic_returns()
EST = estimate(R.iloc[:1000], 252)
EST_LW = estimate(R.iloc[:1000], 252, "ledoit_wolf")


def test_risk_parity_equal_contributions():
    w = risk_parity(EST.cov)
    rc = risk_contributions(w, EST.cov)["Part du risque"]
    assert abs(w.sum() - 1) < 1e-12 and (w > 0).all()
    np.testing.assert_allclose(rc, 1 / 6, atol=1e-6)


def test_target_return_and_vol():
    lo_r = min_variance(EST.mu, EST.cov, 0, 0.4).expected_return
    tgt = (lo_r + max_feasible_return(EST.mu.to_numpy(), 0, 0.4)) / 2
    p = target_portfolio(EST.mu, EST.cov, 0.03, 0, 0.4, target_return=tgt)
    assert abs(p.expected_return - tgt) < 1e-6 and abs(p.weights.sum() - 1) < 1e-8
    v = target_portfolio(EST.mu, EST.cov, 0.03, 0, 0.4, target_vol=p.volatility)
    assert v.volatility <= p.volatility + 1e-6 and v.expected_return >= p.expected_return - 1e-6
    with pytest.raises(ValueError):
        target_portfolio(EST.mu, EST.cov, 0.03, 0, 0.4, target_vol=0.001)


def test_automatic_entries_and_params():
    L = lib.automatic(EST, EST_LW, 0.03, 0, 0.4)
    assert len(L) == 7 and L["SPY"].type == "reference"
    for name, e in L.items():
        if e.type != "reference":
            assert abs(sum(e.poids.values()) - 1) < 1e-8
            assert e.parametres["periode_estimation"][1] == f"{R.index[999]:%Y-%m-%d}"


def test_builder_validation_and_normalize():
    w = {"A": 0.5, "B": 0.3, "C": 0.1}
    assert lib.validate(w, 0, 0.4)  # somme 90 % et A > 40 %
    n = lib.normalize(w)
    assert abs(sum(n.values()) - 1) < 1e-12
    assert lib.validate({"A": 0.4, "B": 0.35, "C": 0.25}, 0, 0.4) == []


def test_json_roundtrip_duplicate_rename():
    L = lib.automatic(EST, EST_LW, 0.03, 0, 0.4)
    new = lib.duplicate(L, "Sharpe maximal")
    lib.rename(L, new, "Mon portefeuille")
    back = lib.from_json(lib.to_json(L))
    assert back["Mon portefeuille"].poids == L["Mon portefeuille"].poids
    with pytest.raises(ValueError):
        lib.rename(L, "Mon portefeuille", "SPY")


def test_library_weights_ignore_future():
    split = R.index[999]
    altered = R.copy()
    altered.loc[altered.index > split] *= -2
    e1 = lib.automatic(estimate(split_returns(R, split)[0], 252), EST_LW, 0.03, 0, 0.4)
    e2 = lib.automatic(estimate(split_returns(altered, split)[0], 252), EST_LW, 0.03, 0, 0.4)
    assert e1["Sharpe maximal"].poids == e2["Sharpe maximal"].poids


def test_attribution_sums_to_portfolio_return():
    from core.analysis import attribution, cumulative_attribution
    from core.portfolio import buy_and_hold_returns
    w = pd.Series([0.4, 0.3, 0.3, 0, 0, 0], index=R.columns)
    r = buy_and_hold_returns(R.iloc[:300], w)
    np.testing.assert_allclose(attribution(R.iloc[:300], w).sum(axis=1), r, atol=1e-12)
    assert abs(cumulative_attribution(R.iloc[:300], w).iloc[-1].sum() - ((1 + r).prod() - 1)) < 1e-10


def test_profile_missing_fields_and_fallback(tmp_path):
    from core.fundamentals import get_profile
    p = get_profile("ABC", fetcher=lambda t: {"longName": "Abc", "sector": "Technology", "currency": "USD"},
                    cache_dir=tmp_path)
    assert p["longName"] == "Abc" and p["trailingPE"] is None
    def boom(t):
        raise ConnectionError("hors ligne")
    q = get_profile("ABC", fetcher=boom, cache_dir=tmp_path)          # repli sur la copie locale
    assert q["longName"] == "Abc" and "Copie locale" in q["_source"]
    r = get_profile("XYZ", fetcher=boom, cache_dir=tmp_path)          # ni réseau ni copie : pas de plantage
    assert r["longName"] is None
