"""
Appels au moteur de calcul, mis en cache (st.cache_data).

Les pages n'appellent que ces fonctions : les mêmes paramètres donnent
exactement les mêmes résultats (fonctions déterministes, graines fixes),
et les calculs lourds ne sont exécutés qu'une fois.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppParams, SENSITIVITY_CAPS, SENSITIVITY_WINDOWS
from core import backtest as bt
from core.optimization import check_optimizer, efficient_frontier, random_portfolios
from core.returns import estimate, periodic_rf, rolling_mean_correlation, simple_returns

TTL = 3600


def log(calcul: str, **parametres) -> None:
    """Ajoute une ligne au journal des calculs de la session (page Sources et méthodologie)."""
    from datetime import datetime
    entry = {"Heure": datetime.now().strftime("%H:%M:%S"), "Calcul": calcul,
             "Paramètres": " · ".join(f"{k} = {v}" for k, v in parametres.items())}
    journal = st.session_state.setdefault("journal", [])
    if not journal or (journal[-1]["Calcul"], journal[-1]["Paramètres"]) != (calcul, entry["Paramètres"]):
        journal.append(entry)
        del journal[:-200]


@st.cache_data(ttl=TTL, show_spinner=False)
def split(prices: pd.DataFrame, split_date, rf: float, lo: float, hi: float, cov_method: str,
          ppy: int) -> bt.SplitResult:
    return bt.static_split(simple_returns(prices), split_date, rf, lo, hi, cov_method, ppy)


@st.cache_data(ttl=TTL, show_spinner=False)
def frontier(mu: pd.Series, cov: pd.DataFrame, rf: float, lo: float, hi: float, n_points: int = 40) -> pd.DataFrame:
    return efficient_frontier(mu, cov, rf, lo, hi, n_points)


@st.cache_data(ttl=TTL, show_spinner=False)
def cloud(mu: pd.Series, cov: pd.DataFrame, rf: float, n: int, lo: float, hi: float) -> pd.DataFrame:
    return random_portfolios(mu, cov, rf, n, lo, hi, seed=42)


@st.cache_data(ttl=TTL, show_spinner=False)
def optimizer_check(cov: pd.DataFrame) -> dict:
    return check_optimizer(cov)


@st.cache_data(ttl=TTL, show_spinner=False)
def estimates(prices: pd.DataFrame, split_date, ppy: int, method: str):
    r = simple_returns(prices)
    return estimate(r.loc[:pd.Timestamp(split_date)], ppy, method)


@st.cache_data(ttl=TTL, show_spinner=False)
def rolling_corr(prices: pd.DataFrame, window: int) -> pd.Series:
    return rolling_mean_correlation(simple_returns(prices), window)


@st.cache_data(ttl=TTL, show_spinner=False)
def realized(prices: pd.DataFrame, split_date, rf: float, lo: float, hi: float, cov_method: str,
             ppy: int) -> pd.DataFrame:
    return bt.realized_frontier(simple_returns(prices), split_date, rf, lo, hi, cov_method, 30, ppy)


def strategies(cap: float) -> list[bt.Strategy]:
    """Les 4 stratégies comparées dans le backtest glissant."""
    return [
        bt.Strategy("Équipondéré (1/N)", "equal"),
        bt.Strategy(f"Variance minimale (plafond {cap:.0%})", "min_variance", "sample", cap),
        bt.Strategy("Sharpe maximal (empirique)", "max_sharpe", "sample", 1.0),
        bt.Strategy(f"Sharpe maximal (Ledoit-Wolf, plafond {cap:.0%})", "max_sharpe", "ledoit_wolf", cap),
    ]


@st.cache_data(ttl=TTL, show_spinner=False)
def rolling(daily_prices: pd.DataFrame, rf: float, window: int, step: int, cost_bps: float,
            cap: float) -> bt.BacktestResult:
    r = simple_returns(daily_prices)
    start = bt.common_start(len(r), [*SENSITIVITY_WINDOWS, window])
    return bt.rolling_backtest(r, strategies(cap), rf, window, step, cost_bps, start_index=start)


@st.cache_data(ttl=TTL, show_spinner=False)
def sensitivity(daily_prices: pd.DataFrame, rf: float, step: int, cost_bps: float) -> tuple[pd.DataFrame, float]:
    return bt.sensitivity_grid(simple_returns(daily_prices), rf, SENSITIVITY_WINDOWS, SENSITIVITY_CAPS,
                               step, cost_bps)


def split_for(params: AppParams, prices: pd.DataFrame, ppy: int, cov_method: str | None = None,
              hi: float | None = None) -> bt.SplitResult:
    """Raccourci : séparation estimation / test avec les paramètres de l'utilisateur."""
    log("Optimisation de Markowitz (estimation / test)", separation=f"{params.split_date:%d/%m/%Y}",
        estimateur=cov_method or params.cov_method, rf=f"{params.risk_free_rate:.2%}",
        plafond=f"{(params.weight_max if hi is None else hi):.0%}", frequence=ppy)
    return split(prices, params.split_date, params.risk_free_rate, params.weight_min,
                 params.weight_max if hi is None else hi, cov_method or params.cov_method, ppy)


def rf_periodic(params: AppParams, ppy: int) -> float:
    return periodic_rf(params.risk_free_rate, ppy)


# --------------------------------------------------------------------------- #
# Ajouts : positions réalisées, sensibilité par durée, diversification
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=TTL, show_spinner=False)
def window_grid(prices: pd.DataFrame, split_date, rf: float, lo: float, cov_method: str,
                ppy: int) -> tuple[pd.DataFrame, float]:
    from config import SENSITIVITY_CAPS
    return bt.window_sensitivity(simple_returns(prices), split_date, rf, [1, 2, 3, 5], SENSITIVITY_CAPS, lo,
                                 cov_method, ppy)


@st.cache_data(ttl=TTL, show_spinner=False)
def extra_prices(tickers: tuple[str, ...], start, end):
    """Téléchargement d'actifs supplémentaires (même chargeur, même cache de secours)."""
    from core.data_loader import load_prices
    return load_prices(list(tickers), start, end)


@st.cache_data(ttl=TTL, show_spinner=False)
def universe(prices: pd.DataFrame, split_date, rf: float, lo: float, hi: float, cov_method: str, ppy: int):
    from core.diversification import analyse_universe
    return analyse_universe(simple_returns(prices), split_date, rf, lo, hi, cov_method, ppy)
