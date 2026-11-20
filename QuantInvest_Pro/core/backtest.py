"""
Validation hors échantillon des portefeuilles de Markowitz.

1. static_split      : estimation sur [début, date de séparation], poids figés,
                       évaluation sur ]date de séparation, fin].
2. realized_frontier : frontière estimée vs position réalisée de ses portefeuilles.
3. rolling_backtest  : réestimation périodique sur fenêtre glissante, dérive des
                       poids entre deux rééquilibrages, frais de transaction.
4. sensitivity_grid  : Sharpe hors échantillon selon la fenêtre et le plafond.

GARANTIE ANTI-ANTICIPATION : à chaque date de décision t, seules les lignes de
rendements d'index ≤ t sont passées à l'estimateur ; les poids décidés en t ne
s'appliquent qu'au rendement de t+1. Les commentaires « [no look-ahead] »
signalent les endroits où cette règle est appliquée.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.optimization import EQUAL, MAX_SHARPE, MIN_VAR, efficient_frontier, equal_weight, max_sharpe, min_variance
from core.portfolio import buy_and_hold_returns, effective_n, fixed_weight_returns, max_drawdown, metrics_table
from core.returns import Estimates, estimate

PERIODS = 252


def optimal_portfolios(est: Estimates, rf: float, lo: float, hi: float) -> dict:
    """Les trois portefeuilles du sujet, calculés sur les mêmes estimations."""
    return {
        MIN_VAR: min_variance(est.mu, est.cov, lo, hi, rf),
        MAX_SHARPE: max_sharpe(est.mu, est.cov, rf, lo, hi),
        EQUAL: equal_weight(est.mu, est.cov, rf),
    }


# --------------------------------------------------------------------------- #
# 1. Séparation estimation / test
# --------------------------------------------------------------------------- #
@dataclass
class SplitResult:
    est: Estimates
    portfolios: dict                      # nom -> OptResult (estimés sur la période d'estimation)
    returns_est: pd.DataFrame             # rendements des portefeuilles, période d'estimation
    returns_test: pd.DataFrame            # rendements des portefeuilles, période de test
    metrics_est: pd.DataFrame
    metrics_test: pd.DataFrame


def split_returns(returns: pd.DataFrame, split_date) -> tuple[pd.DataFrame, pd.DataFrame]:
    split = pd.Timestamp(split_date)
    return returns.loc[:split], returns.loc[returns.index > split]


def static_split(returns: pd.DataFrame, split_date, rf: float, lo: float, hi: float,
                 cov_method: str = "sample", periods_per_year: int = PERIODS,
                 test_mode: str = "buy_and_hold") -> SplitResult:
    """`returns` à la fréquence choisie (252, 52 ou 12 périodes par an).

    Conventions : sur la période d'estimation, poids constants (ce que « voit »
    l'optimiseur) ; sur la période de test, achat à la date de séparation puis
    conservation (poids qui dérivent), sauf test_mode="constant".
    """
    r_est, r_test = split_returns(returns, split_date)
    min_est, min_test = max(periods_per_year // 2, 24), max(periods_per_year // 12, 6)
    if len(r_est) < min_est or len(r_test) < min_test:
        raise ValueError(f"Période trop courte : {len(r_est)} observations d'estimation (min {min_est}) "
                         f"et {len(r_test)} de test (min {min_test}). Déplacez la date de séparation.")
    est = estimate(r_est, periods_per_year, cov_method)  # [no look-ahead] uniquement ≤ date de séparation
    ports = optimal_portfolios(est, rf, lo, hi)
    re = pd.DataFrame({k: fixed_weight_returns(r_est, p.weights) for k, p in ports.items()})
    apply = buy_and_hold_returns if test_mode == "buy_and_hold" else fixed_weight_returns
    rt = pd.DataFrame({k: apply(r_test, p.weights) for k, p in ports.items()})  # poids décidés une seule fois
    return SplitResult(est, ports, re, rt, metrics_table(dict(re.items()), rf, periods_per_year),
                       metrics_table(dict(rt.items()), rf, periods_per_year))


# --------------------------------------------------------------------------- #
# 2. Frontière estimée vs réalisée
# --------------------------------------------------------------------------- #
def realized_frontier(returns: pd.DataFrame, split_date, rf: float, lo: float, hi: float,
                      cov_method: str = "sample", n_points: int = 30,
                      periods_per_year: int = PERIODS) -> pd.DataFrame:
    """Pour chaque portefeuille de la frontière estimée : (σ, μ) estimés et réalisés.
    Mêmes définitions des deux côtés : μ = moyenne × N, σ = écart-type × √N."""
    r_est, r_test = split_returns(returns, split_date)
    est = estimate(r_est, periods_per_year, cov_method)  # [no look-ahead]
    fr = efficient_frontier(est.mu, est.cov, rf, lo, hi, n_points)
    assets = list(est.mu.index)
    W = fr[assets].to_numpy()
    rp = r_test[assets].to_numpy() @ W.T                # T_test × n_points
    fr["rendement_realise"] = rp.mean(axis=0) * periods_per_year
    fr["volatilite_realisee"] = rp.std(axis=0, ddof=1) * np.sqrt(periods_per_year)
    fr["sharpe_realise"] = (fr["rendement_realise"] - rf) / fr["volatilite_realisee"]
    return fr


def realized_points(returns: pd.DataFrame, split_date, portfolios: dict, rf: float,
                    periods_per_year: int = PERIODS) -> pd.DataFrame:
    """Position (σ, μ) annoncée puis réalisée de portefeuilles donnés, mêmes poids,
    mêmes définitions que la frontière (poids constants, μ = moyenne × N)."""
    _, r_test = split_returns(returns, split_date)
    rows = {}
    for name, p in portfolios.items():
        rp = fixed_weight_returns(r_test, p.weights)
        mu, vol = rp.mean() * periods_per_year, rp.std(ddof=1) * np.sqrt(periods_per_year)
        rows[name] = {"rendement": p.expected_return, "volatilite": p.volatility, "sharpe": p.sharpe,
                      "rendement_realise": mu, "volatilite_realisee": vol, "sharpe_realise": (mu - rf) / vol}
    return pd.DataFrame(rows).T


def window_sensitivity(returns: pd.DataFrame, split_date, rf: float, years: list[int], caps: list[float],
                       lo: float = 0.0, cov_method: str = "sample",
                       periods_per_year: int = PERIODS) -> tuple[pd.DataFrame, float]:
    """Sharpe en test (achat puis conservation) du Sharpe maximal estimé sur les
    `years` dernières années avant la date de séparation, pour chaque plafond.
    NaN si l'historique disponible couvre moins de 95 % de la durée demandée."""
    split = pd.Timestamp(split_date)
    r_test = returns.loc[returns.index > split]
    grid = pd.DataFrame(index=years, columns=caps, dtype=float)
    for y in years:
        window = returns.loc[(returns.index > split - pd.DateOffset(years=y)) & (returns.index <= split)]
        if len(window) < 0.95 * y * periods_per_year:
            continue
        est = estimate(window, periods_per_year, cov_method)          # [no look-ahead] ≤ date de séparation
        for c in caps:
            hi = max(c, 1 / returns.shape[1])
            w = max_sharpe(est.mu, est.cov, rf, lo, hi).weights
            grid.loc[y, c] = metrics_table({"x": buy_and_hold_returns(r_test, w)}, rf, periods_per_year).loc["x", "Sharpe"]
    eq = pd.Series(1 / returns.shape[1], index=returns.columns)
    ref = metrics_table({"x": buy_and_hold_returns(r_test, eq)}, rf, periods_per_year).loc["x", "Sharpe"]
    return grid, float(ref)


def crisis_performance(series: dict[str, pd.Series], crises: list[tuple[str, str, str]]) -> pd.DataFrame:
    """Rendement cumulé et drawdown maximal de chaque série pendant chaque crise."""
    rows = []
    for label, a, b in crises:
        for name, r in series.items():
            seg = r.loc[a:b].dropna()
            if len(seg) < 5:
                continue
            rows.append({"Crise": label, "Portefeuille": name, "Rendement cumulé": float((1 + seg).prod() - 1),
                         "Drawdown maximal": max_drawdown(seg), "Séances": len(seg)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# 3. Backtest en fenêtre glissante
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Strategy:
    name: str
    objective: str            # "equal", "min_variance" ou "max_sharpe"
    cov_method: str = "sample"
    cap: float = 1.0


@dataclass
class BacktestResult:
    returns: pd.DataFrame                    # rendements nets de frais, une colonne par stratégie
    weights: dict[str, pd.DataFrame]         # poids quotidiens (après dérive) par stratégie
    decisions: dict[str, pd.DataFrame]       # par décision : date, poids cibles, rotation, Sharpe annoncé
    window: int
    step: int
    cost_bps: float
    start: pd.Timestamp
    failures: dict[str, int] = field(default_factory=dict)  # nb de non-convergences

    def summary(self, rf: float) -> pd.DataFrame:
        tab = metrics_table(dict(self.returns.items()), rf)
        years = len(self.returns) / PERIODS
        tab["Rotation annuelle"] = [self.decisions[s]["rotation"].sum() / years for s in self.returns]
        tab["Nb effectif de titres"] = [self.decisions[s]["n_effectif"].mean() for s in self.returns]
        tab["Sharpe annoncé (moyen)"] = [self.decisions[s]["sharpe_annonce"].mean() for s in self.returns]
        return tab


def _target_weights(strat: Strategy, window_returns: pd.DataFrame, rf: float, lo: float):
    n = window_returns.shape[1]
    if strat.objective == "equal":
        w = np.full(n, 1 / n)
        est = estimate(window_returns, PERIODS, "sample")
        ex = float(w @ est.mu.to_numpy() - rf)
        return w, ex / float(np.sqrt(w @ est.cov.to_numpy() @ w)), True
    est = estimate(window_returns, PERIODS, strat.cov_method)
    hi = max(strat.cap, 1 / n)                       # plafond toujours faisable
    res = (min_variance(est.mu, est.cov, lo, hi, rf) if strat.objective == "min_variance"
           else max_sharpe(est.mu, est.cov, rf, lo, hi))
    return res.weights.to_numpy(), res.sharpe, res.converged


def rolling_backtest(returns: pd.DataFrame, strategies: list[Strategy], rf: float, window: int = 252,
                     step: int = 21, cost_bps: float = 10.0, lo: float = 0.0,
                     start_index: int | None = None) -> BacktestResult:
    """Rééquilibrage tous les `step` séances, estimation sur les `window` dernières.

    À l'indice de décision t (clôture de la séance t) :
      - estimation sur returns[t−window+1 … t]               [no look-ahead]
      - rotation = Σ|w_cible − w_dérivé| ; frais = bps/10 000 × rotation,
        déduits de la valeur du portefeuille à la séance t ;
      - entre deux décisions, w dérive : wᵢ ← wᵢ(1 + rᵢ) / (1 + r_p).
    La première décision part de 100 % de liquidités (rotation = 1).
    """
    R = returns.to_numpy()
    T, n = R.shape
    t0 = window - 1 if start_index is None else max(start_index, window - 1)
    if t0 >= T - 1:
        raise ValueError(f"Historique insuffisant : {T} séances pour une fenêtre de {window}.")
    cost_rate = cost_bps / 10_000
    decision_idx = set(range(t0, T - 1, step))
    dates = returns.index
    out_r, out_w, out_d, fails = {}, {}, {}, {}

    for strat in strategies:
        w = np.zeros(n)                       # liquidités avant la 1re décision
        net = np.empty(T - t0)
        wh = np.empty((T - t0, n))
        rows, n_fail = [], 0
        for k, t in enumerate(range(t0, T)):
            if k == 0:
                r_p = 0.0                     # séance t0 : on est encore en liquidités
            else:
                r_p = float(w @ R[t])         # w décidé à t−1 (ou avant) appliqué à r_t
                w = w * (1 + R[t]) / (1 + r_p)
            cost = 0.0
            if t in decision_idx:
                window_r = returns.iloc[t - window + 1: t + 1]   # [no look-ahead] lignes ≤ t
                target, sr_ex_ante, ok = _target_weights(strat, window_r, rf, lo)
                n_fail += not ok
                turnover = float(np.abs(target - w).sum())
                cost = cost_rate * turnover
                rows.append({"date": dates[t], "rotation": turnover, "sharpe_annonce": sr_ex_ante,
                             "n_effectif": effective_n(target), "converged": ok,
                             **dict(zip(returns.columns, target))})
                w = target
            net[k] = (1 + r_p) * (1 - cost) - 1
            wh[k] = w
        idx = dates[t0:]
        out_r[strat.name] = pd.Series(net, index=idx)
        out_w[strat.name] = pd.DataFrame(wh, index=idx, columns=returns.columns)
        out_d[strat.name] = pd.DataFrame(rows).set_index("date")
        fails[strat.name] = n_fail
    return BacktestResult(pd.DataFrame(out_r), out_w, out_d, window, step, cost_bps, dates[t0], fails)


def realized_forward_sharpe(net_returns: pd.Series, decision_dates: pd.Index, rf: float,
                            horizon: int = PERIODS) -> pd.Series:
    """Sharpe réalisé sur les `horizon` séances suivant chaque décision
    (NaN si l'horizon complet n'est pas encore observé)."""
    rf_p = (1 + rf) ** (1 / PERIODS) - 1
    pos = net_returns.index.get_indexer(decision_dates)
    out = []
    for p in pos:
        seg = net_returns.iloc[p + 1: p + 1 + horizon]
        out.append((seg.mean() - rf_p) / seg.std(ddof=1) * np.sqrt(PERIODS) if len(seg) == horizon else np.nan)
    return pd.Series(out, index=decision_dates, name="Sharpe réalisé (12 mois suivants)")


# --------------------------------------------------------------------------- #
# 4. Sensibilité
# --------------------------------------------------------------------------- #
def common_start(n_obs: int, windows: list[int], min_test: int = PERIODS) -> int:
    """Indice de départ commun : après la fenêtre la plus longue faisable,
    pour que toutes les configurations soient évaluées sur la même période."""
    feasible = [w for w in windows if w + min_test <= n_obs]
    if not feasible:
        raise ValueError("Historique trop court pour l'analyse de sensibilité.")
    return max(feasible) - 1


def sensitivity_grid(returns: pd.DataFrame, rf: float, windows: list[int], caps: list[float],
                     step: int = 21, cost_bps: float = 10.0, cov_method: str = "sample") -> tuple[pd.DataFrame, float]:
    """Sharpe hors échantillon du Sharpe maximal (fenêtre × plafond) et du 1/N
    de référence, tous évalués sur la même période."""
    start = common_start(len(returns), windows)
    grid = pd.DataFrame(index=windows, columns=caps, dtype=float)
    for win in windows:
        if win - 1 > start:
            continue
        strats = [Strategy(f"cap{c}", "max_sharpe", cov_method, c) for c in caps]
        bt = rolling_backtest(returns, strats, rf, win, step, cost_bps, start_index=start)
        sharpe = bt.summary(rf)["Sharpe"]
        for c in caps:
            grid.loc[win, c] = sharpe[f"cap{c}"]
    ref = rolling_backtest(returns, [Strategy(EQUAL, "equal")], rf, min(windows), step, cost_bps,
                           start_index=start).summary(rf)["Sharpe"].iloc[0]
    return grid, float(ref)
