"""Tests de la collecte (core/data_loader) et du nettoyage (core/preprocessing).

Le téléchargement Yahoo est remplacé par un faux téléchargeur : les tests
vérifient la logique (repli sur cache, échecs, alignement), pas le réseau.
Les séries synthétiques ci-dessous ne servent qu'aux tests.
"""
from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from core.data_loader import extract_close, load_prices
from core.preprocessing import DataQualityError, clean_prices, resample_prices

DATES = pd.bdate_range("2024-01-01", periods=120)


def _series(seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(DATES)))), index=DATES)


FULL = pd.DataFrame({"AAA": _series(1), "BBB": _series(2), "SPY": _series(3)})


def fake_downloader(available: set[str]):
    def dl(tickers, start, end):
        out = FULL.reindex(columns=tickers).copy()
        for t in tickers:
            if t not in available:
                out[t] = np.nan
        return out
    return dl


def _load(tmp_path, available, **kw):
    return load_prices(["AAA", "BBB", "SPY"], date(2024, 1, 1), date(2024, 12, 31), cache_dir=tmp_path,
                       downloader=fake_downloader(available), currency_fn=lambda t: "USD",
                       retry_delay=0, now=lambda: datetime(2026, 11, 20, 15, 0), **kw)


def test_extract_close_multiindex():
    cols = pd.MultiIndex.from_product([["Close", "Open"], ["AAA", "BBB"]])
    raw = pd.DataFrame(np.arange(8.0).reshape(2, 4), columns=cols)
    out = extract_close(raw, ["AAA", "BBB"])
    assert list(out.columns) == ["AAA", "BBB"] and out.iloc[0].tolist() == [0.0, 1.0]


def test_extract_close_empty_result():
    assert extract_close(pd.DataFrame(), ["AAA"]).empty


def test_live_download_fills_cache(tmp_path):
    md = _load(tmp_path, {"AAA", "BBB", "SPY"})
    assert md.status == "live" and md.failed == []
    assert md.prices.shape == (len(DATES), 3)
    assert (tmp_path / "AAA.parquet").exists() and md.currencies["AAA"] == "USD"


def test_fallback_to_cache_when_yahoo_fails(tmp_path):
    _load(tmp_path, {"AAA", "BBB", "SPY"})          # 1er passage : remplit le cache
    md = _load(tmp_path, {"AAA", "SPY"})            # BBB en échec
    assert md.source["BBB"] == "cache" and md.status == "cache"
    pd.testing.assert_series_equal(md.prices["BBB"], FULL["BBB"], check_names=False, check_freq=False)


def test_missing_without_cache_is_reported_not_invented(tmp_path):
    md = _load(tmp_path, {"AAA", "SPY"})
    assert md.failed == ["BBB"] and "BBB" not in md.prices.columns


def test_total_failure_status_error(tmp_path):
    md = _load(tmp_path, set())
    assert md.status == "error" and md.prices.empty


def test_downloader_exception_is_caught(tmp_path):
    def boom(*a):
        raise ConnectionError("réseau coupé")
    md = load_prices(["AAA"], date(2024, 1, 1), date(2024, 2, 1), cache_dir=tmp_path,
                     downloader=boom, currency_fn=lambda t: None, retry_delay=0)
    assert md.status == "error" and any("impossible" in m for m in md.messages)


# ----------------------------- nettoyage ---------------------------------- #
def test_clean_aligns_on_common_dates_and_limits_ffill():
    df = FULL.copy()
    df.iloc[10, 0] = np.nan                 # 1 jour férié : complété
    df.iloc[20:26, 1] = np.nan              # 6 jours de trou : > limite de 3 → dates supprimées
    res = clean_prices(df, ffill_limit=3, min_obs=50)
    assert res.prices.notna().all().all()
    assert res.prices.loc[DATES[10], "AAA"] == df.iloc[9, 0]          # report de la veille
    assert len(res.prices) == len(DATES) - 3                          # 6 manquants − 3 complétés
    assert res.quality.loc["AAA", "Valeurs complétées"] == 1


def test_clean_never_backfills():
    df = FULL.copy()
    df.iloc[0, 0] = np.nan                  # premier prix manquant : ne doit pas être rempli
    res = clean_prices(df, min_obs=50)
    assert res.start == DATES[1]


def test_clean_excludes_short_history_and_invalid_prices():
    df = FULL.copy()
    df.iloc[:60, 2] = np.nan                # SPY : 50 % manquant → exclu
    df.iloc[5, 0] = -1.0                    # prix négatif → invalide
    res = clean_prices(df, min_obs=50)
    assert "SPY" in res.excluded and "SPY" not in res.prices.columns
    assert res.quality.loc["AAA", "Prix invalides"] == 1


def test_clean_raises_when_too_few_observations():
    with pytest.raises(DataQualityError):
        clean_prices(FULL.iloc[:20], min_obs=60)


def test_resample_monthly_takes_last_price():
    m = resample_prices(FULL, "ME")
    assert m.loc["2024-01-31", "AAA"] == FULL.loc["2024-01-31", "AAA"]
