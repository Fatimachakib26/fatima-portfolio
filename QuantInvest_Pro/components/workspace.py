"""
Espace de travail partagé par les pages d'analyse : bibliothèque de portefeuilles
et barre de sélection globale (portefeuilles, actifs, période, indice, fréquence).
La sélection est conservée d'une page à l'autre dans st.session_state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from components.data_service import MarketBundle
from components.formatting import num
from config import CRISES, FREQUENCIES, AppParams
from core import library as lib
from core.preprocessing import resample_prices
from core.returns import estimate, simple_returns

PERIODS = ["Estimation", "Test", "Toute la période", "Krach Covid 2020", "Hausse des taux 2022", "Personnalisée"]


@st.cache_data(ttl=3600, show_spinner=False)
def _automatic(prices: pd.DataFrame, split, rf: float, lo: float, hi: float, benchmark: str | None):
    r = simple_returns(prices).loc[:pd.Timestamp(split)]           # [no look-ahead] période d'estimation
    return lib.automatic(estimate(r, 252, "sample"), estimate(r, 252, "ledoit_wolf"), rf, lo, hi, benchmark)


def get_library(params: AppParams, bundle: MarketBundle) -> dict[str, lib.Entry]:
    auto = _automatic(bundle.daily_prices, params.split_date, params.risk_free_rate, params.weight_min,
                      params.weight_max, bundle.benchmark)
    custom = st.session_state.setdefault("library_custom", {})
    return {**auto, **custom}


@dataclass
class Selection:
    portfolios: list[str]
    assets: list[str]
    period: str
    start: pd.Timestamp
    end: pd.Timestamp
    show_bench: bool
    frequency: str

    @property
    def label(self) -> str:
        return f"{self.period} ({self.start:%d/%m/%Y} – {self.end:%d/%m/%Y})"


def _persist(key: str) -> None:
    st.session_state[key] = st.session_state[f"w_{key}"]


def resolve_period(period: str, params: AppParams, bundle: MarketBundle, custom=None) -> tuple[pd.Timestamp, pd.Timestamp]:
    idx = bundle.daily_prices.index
    split = pd.Timestamp(params.split_date)
    first, last = idx[0], idx[-1]
    crises = {c[0]: (pd.Timestamp(c[1]), pd.Timestamp(c[2])) for c in CRISES}
    if period == "Estimation":
        return first, min(split, last)
    if period == "Test":
        return idx[idx > split][0] if (idx > split).any() else last, last
    if period == "Krach Covid 2020":
        return crises["Krach Covid"]
    if period == "Hausse des taux 2022":
        return crises["Hausse des taux 2022"]
    if period == "Personnalisée" and custom and len(custom) == 2:
        return pd.Timestamp(custom[0]), pd.Timestamp(custom[1])
    return first, last


def selection_bar(library: dict, bundle: MarketBundle, params: AppParams, show_assets: bool = False,
                  max_portfolios: int = 6, default_period: str = "Test") -> Selection:
    ss = st.session_state
    names = list(library)
    ss.setdefault("sel_portfolios", [n for n in ["Sharpe maximal", "Variance minimale", "Équipondéré (1/N)"] if n in names])
    ss["sel_portfolios"] = [n for n in ss["sel_portfolios"] if n in names] or names[:1]
    ss.setdefault("sel_assets", list(bundle.assets))
    ss["sel_assets"] = [a for a in ss["sel_assets"] if a in bundle.assets] or list(bundle.assets)
    ss.setdefault("sel_period", default_period)
    ss.setdefault("sel_bench", True)
    ss.setdefault("sel_freq", params.frequency)
    ss.setdefault("sel_custom", (params.start_date, params.end_date))
    for k in ("portfolios", "assets", "period", "bench", "freq", "custom"):
        ss[f"w_sel_{k}"] = ss[f"sel_{k}"]
    with st.container(border=True):
        c1, c2 = st.columns([2.2, 3])
        c1.multiselect("Portefeuilles", names, key="w_sel_portfolios", max_selections=max_portfolios,
                       on_change=_persist, args=("sel_portfolios",),
                       format_func=lambda n: ("● " if library[n].type != "reference" else "◆ ") + n)
        c2.segmented_control("Période", PERIODS, key="w_sel_period", required=True, on_change=_persist, args=("sel_period",))
        c3, c4, c5 = st.columns([2.2, 1.6, 1.4])
        if show_assets:
            c3.multiselect("Actifs", bundle.assets, key="w_sel_assets", on_change=_persist, args=("sel_assets",))
        if (ss["sel_period"] or "Test") == "Personnalisée":
            c4.date_input("Dates", key="w_sel_custom", on_change=_persist, args=("sel_custom",), format="DD/MM/YYYY",
                          min_value=bundle.daily_prices.index[0].date(), max_value=bundle.daily_prices.index[-1].date())
        c5.segmented_control("Fréquence", list(FREQUENCIES), key="w_sel_freq", required=True, on_change=_persist, args=("sel_freq",))
        c4b = c4 if (ss["sel_period"] or "Test") != "Personnalisée" else c3
        c4b.toggle(f"Afficher {bundle.benchmark or 'SPY'}", key="w_sel_bench", on_change=_persist, args=("sel_bench",),
                   disabled=bundle.benchmark is None)
    period = ss["sel_period"] or "Test"
    start, end = resolve_period(period, params, bundle, ss.get("sel_custom"))
    sel = Selection(list(ss["sel_portfolios"]), list(ss["sel_assets"]), period, start, end,
                    bool(ss["sel_bench"]) and bundle.benchmark is not None, ss["sel_freq"] or params.frequency)
    n_obs = len(bundle.daily_prices.loc[start:end])
    stamp = bundle.raw.as_of
    st.caption(f"Données : Yahoo Finance · mise à jour le {stamp:%d/%m/%Y à %H:%M} · période {sel.label} · "
               f"{num(n_obs, 0)} séances · fréquence {sel.frequency.lower()} · poids estimés jusqu'au "
               f"{params.split_date:%d/%m/%Y} (jamais réestimés sur la période affichée)" if stamp else "")
    return sel


def period_returns(sel: Selection, bundle: MarketBundle) -> tuple[pd.DataFrame, pd.Series | None, int]:
    """Rendements des actifs (et de l'indice) sur la période et à la fréquence choisies."""
    rule, ppy = FREQUENCIES[sel.frequency]
    prices = bundle.clean.prices.loc[sel.start - pd.Timedelta(days=7):sel.end]
    prices = resample_prices(prices, rule)
    r = simple_returns(prices).loc[sel.start:sel.end]
    bench = r[bundle.benchmark] if bundle.benchmark else None
    return r[bundle.assets], bench, ppy


def portfolio_returns(names: list[str], library: dict, assets_r: pd.DataFrame, bench_r) -> dict[str, pd.Series]:
    out = {}
    for n in names:
        try:
            out[n] = lib.entry_returns(library[n], assets_r, bench_r)
        except ValueError as exc:
            st.warning(f"« {n} » ignoré : {exc}")
    return out
