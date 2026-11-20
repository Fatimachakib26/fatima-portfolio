"""
Optimisation de Markowitz (SciPy SLSQP).

Problèmes résolus, sous Σwᵢ = 1 et w_min ≤ wᵢ ≤ w_max :
- variance minimale :   min  wᵀΣw
- Sharpe maximal :      max  (wᵀμ − r_f) / √(wᵀΣw)
- frontière efficiente : min wᵀΣw  sous wᵀμ = cible, pour une grille de cibles
Référence : 1/N (équipondéré), sans estimation.

Chaque résultat indique si l'optimiseur a convergé ET si les contraintes sont
respectées (vérification indépendante après résolution).

Améliorations par rapport à MarkowitzModel.py du cours : taux sans risque
dans le Sharpe, gradients analytiques, plusieurs points de départ
(déterministes), bornes modifiables, contrôle par la formule fermée.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

MIN_VAR, MAX_SHARPE, EQUAL = "Variance minimale", "Sharpe maximal", "Équipondéré (1/N)"
TOL = 1e-6


@dataclass
class OptResult:
    weights: pd.Series
    converged: bool
    message: str
    expected_return: float
    volatility: float
    sharpe: float


def portfolio_stats(w: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf: float) -> tuple[float, float, float]:
    ret = float(w @ mu)
    vol = float(np.sqrt(max(w @ cov @ w, 0.0)))
    return ret, vol, (ret - rf) / vol if vol > 0 else float("nan")


def check_feasible(n: int, lo: float, hi: float) -> None:
    if not (lo <= hi and n * lo <= 1 + 1e-12 and n * hi >= 1 - 1e-12):
        raise ValueError(f"Contraintes infaisables : {n} actifs avec des poids entre {lo:.0%} et {hi:.0%}.")


def _validate(w: np.ndarray, lo: float, hi: float) -> bool:
    return abs(w.sum() - 1) < TOL and w.min() >= lo - TOL and w.max() <= hi + TOL


def _clean(w: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Supprime le bruit numérique (ex. −1e-17) sans fausser les contraintes."""
    w = np.clip(w, lo, hi)
    return w / w.sum() if abs(w.sum() - 1) < 1e-4 else w


def _starts(n: int, lo: float, hi: float, mu: np.ndarray) -> list[np.ndarray]:
    """Points de départ déterministes : équipondéré + portefeuilles « en coin »."""
    eq = np.full(n, 1.0 / n)
    starts = [eq]
    for i in np.argsort(-mu)[:3]:  # orientés vers les meilleurs rendements
        w = np.full(n, float(lo))
        rest = 1 - w.sum()
        add = min(hi - lo, rest)
        w[i] += add
        rest -= add
        others = [j for j in range(n) if j != i]
        w[others] += rest / len(others)
        if _validate(w, lo, hi):
            starts.append(w)
    return starts


def _solve(fun, jac, n, lo, hi, x0s, extra_cons=()) -> tuple[np.ndarray, bool, str]:
    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones_like(w)}, *extra_cons]
    best = None
    for x0 in x0s:
        res = minimize(fun, x0, jac=jac, method="SLSQP", bounds=[(lo, hi)] * n, constraints=cons,
                       options={"ftol": 1e-12, "maxiter": 1000})
        ok = res.success and _validate(res.x, lo, hi) and all(abs(c["fun"](res.x)) < 1e-6 for c in extra_cons)
        if best is None or (ok and (not best[1] or res.fun < best[0].fun - 1e-12)):
            best = (res, ok)
    res, ok = best
    return _clean(res.x, lo, hi), ok, "Convergence atteinte" if ok else f"Échec de l'optimiseur : {res.message}"


def _result(w, assets, mu, cov, rf, ok, msg) -> OptResult:
    ret, vol, sr = portfolio_stats(w, mu, cov, rf)
    return OptResult(pd.Series(w, index=assets), ok, msg, ret, vol, sr)


def min_variance(mu: pd.Series, cov: pd.DataFrame, lo: float = 0.0, hi: float = 1.0, rf: float = 0.0) -> OptResult:
    n = len(mu)
    check_feasible(n, lo, hi)
    S = cov.to_numpy()
    w, ok, msg = _solve(lambda w: w @ S @ w, lambda w: 2 * S @ w, n, lo, hi, [np.full(n, 1 / n)])
    return _result(w, mu.index, mu.to_numpy(), S, rf, ok, msg)


def max_sharpe(mu: pd.Series, cov: pd.DataFrame, rf: float, lo: float = 0.0, hi: float = 1.0) -> OptResult:
    n = len(mu)
    check_feasible(n, lo, hi)
    m, S = mu.to_numpy(), cov.to_numpy()

    def neg_sharpe(w):
        v = np.sqrt(w @ S @ w)
        return -(w @ m - rf) / v

    def grad(w):
        v = np.sqrt(w @ S @ w)
        ex = w @ m - rf
        return -(m * v - ex * (S @ w) / v) / v**2

    w, ok, msg = _solve(neg_sharpe, grad, n, lo, hi, _starts(n, lo, hi, m))
    return _result(w, mu.index, m, S, rf, ok, msg)


def equal_weight(mu: pd.Series, cov: pd.DataFrame, rf: float) -> OptResult:
    n = len(mu)
    return _result(np.full(n, 1 / n), mu.index, mu.to_numpy(), cov.to_numpy(), rf, True, "Sans optimisation")


def max_feasible_return(mu: np.ndarray, lo: float, hi: float) -> float:
    """Rendement maximal atteignable sous les bornes (allocation gloutonne)."""
    w = np.full(len(mu), float(lo))
    rest = 1 - w.sum()
    for i in np.argsort(-mu):
        add = min(hi - lo, rest)
        w[i] += add
        rest -= add
    return float(w @ mu)


def efficient_frontier(mu: pd.Series, cov: pd.DataFrame, rf: float, lo: float = 0.0, hi: float = 1.0,
                       n_points: int = 30) -> pd.DataFrame:
    """Frontière exacte : variance minimale pour chaque rendement cible.

    Retourne un DataFrame (une ligne par portefeuille) : rendement, volatilité,
    sharpe, converged, puis une colonne de poids par actif.
    """
    n = len(mu)
    m, S = mu.to_numpy(), cov.to_numpy()
    gmv = min_variance(mu, cov, lo, hi, rf)
    r_lo, r_hi = gmv.expected_return, max_feasible_return(m, lo, hi)
    rows = []
    prev = gmv.weights.to_numpy()
    for target in np.linspace(r_lo, r_hi, n_points):
        con = {"type": "eq", "fun": lambda w, t=target: w @ m - t, "jac": lambda w: m}
        w, ok, _ = _solve(lambda w: w @ S @ w, lambda w: 2 * S @ w, n, lo, hi, [prev, np.full(n, 1 / n)], (con,))
        prev = w
        ret, vol, sr = portfolio_stats(w, m, S, rf)
        rows.append({"rendement": ret, "volatilite": vol, "sharpe": sr, "converged": ok,
                     **dict(zip(mu.index, w))})
    return pd.DataFrame(rows)


def random_portfolios(mu: pd.Series, cov: pd.DataFrame, rf: float, n_portfolios: int = 5000,
                      lo: float = 0.0, hi: float = 1.0, seed: int = 42) -> pd.DataFrame:
    """Nuage illustratif de portefeuilles admissibles (tirages de Dirichlet,
    graine fixe → résultats reproductibles). Seuls les tirages respectant les
    bornes sont conservés."""
    rng = np.random.default_rng(seed)
    n = len(mu)
    m, S = mu.to_numpy(), cov.to_numpy()
    kept = []
    for _ in range(20):  # quelques lots suffisent, même avec un plafond
        w = rng.dirichlet(np.ones(n), size=n_portfolios)
        w = w[(w.min(axis=1) >= lo - 1e-12) & (w.max(axis=1) <= hi + 1e-12)]
        kept.append(w)
        if sum(len(k) for k in kept) >= n_portfolios:
            break
    W = np.vstack(kept)[:n_portfolios]
    rets = W @ m
    vols = np.sqrt(np.einsum("ij,jk,ik->i", W, S, W))
    df = pd.DataFrame(W, columns=mu.index)
    df.insert(0, "sharpe", (rets - rf) / vols)
    df.insert(0, "volatilite", vols)
    df.insert(0, "rendement", rets)
    return df


# --------------------------------------------------------------------------- #
# Contrôle de l'optimiseur par la formule fermée
# --------------------------------------------------------------------------- #
def min_variance_analytic(cov: pd.DataFrame) -> pd.Series:
    """Variance minimale SANS bornes (ventes à découvert permises) :
    w* = Σ⁻¹1 / (1ᵀ Σ⁻¹ 1)   (solution du lagrangien de min wᵀΣw s.c. 1ᵀw = 1)."""
    ones = np.ones(len(cov))
    x = np.linalg.solve(cov.to_numpy(), ones)  # Σ⁻¹1 sans inverser explicitement Σ
    return pd.Series(x / x.sum(), index=cov.index)


def check_optimizer(cov: pd.DataFrame, bound: float = 10.0) -> dict:
    """Compare SLSQP (bornes ±`bound`, quasi non contraintes) à la formule exacte."""
    analytic = min_variance_analytic(cov)
    mu0 = pd.Series(0.0, index=cov.index)
    numeric = min_variance(mu0, cov, lo=-bound, hi=bound)
    diff = float((analytic - numeric.weights).abs().max())
    return {"analytique": analytic, "numerique": numeric.weights, "ecart_max": diff,
            "ok": diff < 1e-4 and numeric.converged}


def risk_parity(cov: pd.DataFrame) -> pd.Series:
    """Parité de risque (contributions égales au risque, ERC, sans vente à découvert).

    On minimise ½ yᵀΣy − (1/n) Σ log yᵢ (y > 0), puis w = y / Σy : à l'optimum,
    yᵢ (Σy)ᵢ = 1/n pour tout i, donc chaque actif contribue autant au risque.
    """
    from scipy.optimize import minimize as _min

    S = cov.to_numpy()
    n = len(S)
    b = np.full(n, 1 / n)
    y0 = 1 / np.sqrt(np.diag(S))
    res = _min(lambda y: 0.5 * y @ S @ y - b @ np.log(y), y0, jac=lambda y: S @ y - b / y,
               method="L-BFGS-B", bounds=[(1e-10, None)] * n, options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 5000})
    w = res.x / res.x.sum()
    return pd.Series(w, index=cov.index)


def target_portfolio(mu: pd.Series, cov: pd.DataFrame, rf: float, lo: float, hi: float,
                     target_return: float | None = None, target_vol: float | None = None) -> OptResult:
    """Portefeuille de la frontière pour un rendement cible (variance minimale)
    ou une volatilité cible (rendement maximal sous σ ≤ cible)."""
    n = len(mu)
    check_feasible(n, lo, hi)
    m, S = mu.to_numpy(), cov.to_numpy()
    if target_return is not None:
        r_min = min_variance(mu, cov, lo, hi, rf).expected_return
        r_max = max_feasible_return(m, lo, hi)
        if not r_min - 1e-9 <= target_return <= r_max + 1e-9:
            raise ValueError(f"Rendement cible hors de la frontière : choisir entre {r_min:.1%} et {r_max:.1%}.")
        con = {"type": "eq", "fun": lambda w: w @ m - target_return, "jac": lambda w: m}
        w, ok, msg = _solve(lambda w: w @ S @ w, lambda w: 2 * S @ w, n, lo, hi, [np.full(n, 1 / n)], (con,))
    else:
        v_min = min_variance(mu, cov, lo, hi, rf).volatility
        if target_vol < v_min - 1e-9:
            raise ValueError(f"Volatilité cible trop faible : le minimum atteignable est {v_min:.1%}.")
        con = {"type": "ineq", "fun": lambda w: target_vol**2 - w @ S @ w, "jac": lambda w: -2 * S @ w}
        cons = [{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones_like(w)}, con]
        best = None
        for x0 in [min_variance(mu, cov, lo, hi, rf).weights.to_numpy(), np.full(n, 1 / n)]:
            r = minimize(lambda w: -(w @ m), x0, jac=lambda w: -m, method="SLSQP", bounds=[(lo, hi)] * n,
                         constraints=cons, options={"ftol": 1e-12, "maxiter": 1000})
            if r.success and (best is None or r.fun < best.fun):
                best = r
        if best is None:
            raise ValueError("L'optimiseur n'a pas convergé pour cette volatilité cible.")
        w, ok, msg = _clean(best.x, lo, hi), True, "Convergence atteinte"
    return _result(w, mu.index, m, S, rf, ok, msg)


def optimize_custom(mu: pd.Series, cov: pd.DataFrame, rf: float, objective: str, lower: pd.Series, upper: pd.Series,
                    groups: dict[str, list[str]] | None = None, group_caps: dict[str, float] | None = None) -> OptResult:
    """Variance minimale ou Sharpe maximal avec bornes PAR ACTIF et plafonds par groupe (secteur).
    Lève ValueError avec un message clair si les contraintes sont impossibles."""
    assets = list(mu.index)
    lo, hi = lower.reindex(assets).to_numpy(float), upper.reindex(assets).to_numpy(float)
    if (lo > hi + 1e-12).any():
        bad = [a for a, l, h in zip(assets, lo, hi) if l > h]
        raise ValueError(f"Minimum supérieur au maximum pour : {', '.join(bad)}.")
    if lo.sum() > 1 + 1e-9:
        raise ValueError(f"La somme des minimums ({lo.sum():.0%}) dépasse 100 %.")
    if hi.sum() < 1 - 1e-9:
        raise ValueError(f"La somme des maximums ({hi.sum():.0%}) est inférieure à 100 %.")
    cons = []
    for g, members in (groups or {}).items():
        cap = (group_caps or {}).get(g)
        if cap is None or cap >= 1:
            continue
        idx = [assets.index(a) for a in members if a in assets]
        if lo[idx].sum() > cap + 1e-9:
            raise ValueError(f"Secteur « {g} » : les minimums ({lo[idx].sum():.0%}) dépassent le plafond ({cap:.0%}).")
        cons.append({"type": "ineq", "fun": lambda w, i=idx, c=cap: c - w[i].sum()})
    if cons:  # capacité maximale : min(plafond, Σ max) par secteur + Σ max des actifs hors secteur plafonné
        grouped = {a for m in (groups or {}).values() for a in m}
        capacity = sum(min((group_caps or {}).get(g, 1.0), hi[[assets.index(a) for a in m if a in assets]].sum())
                       for g, m in (groups or {}).items())
        capacity += sum(h for a, h in zip(assets, hi) if a not in grouped)
        if capacity < 1 - 1e-9:
            raise ValueError("Les plafonds par secteur ne permettent pas d'investir 100 % du capital.")
    m_, S = mu.to_numpy(), cov.to_numpy()
    n = len(assets)
    base = [{"type": "eq", "fun": lambda w: w.sum() - 1, "jac": lambda w: np.ones_like(w)}, *cons]
    if objective == "min_variance":
        fun, jac = (lambda w: w @ S @ w), (lambda w: 2 * S @ w)
    else:
        def fun(w):
            return -(w @ m_ - rf) / np.sqrt(w @ S @ w)
        jac = None
    x0 = np.clip(np.full(n, 1 / n), lo, hi)
    x0 = x0 / x0.sum()
    res = minimize(fun, x0, jac=jac, method="SLSQP", bounds=list(zip(lo, hi)), constraints=base,
                   options={"ftol": 1e-12, "maxiter": 2000})
    w = np.clip(res.x, lo, hi)
    ok = res.success and abs(w.sum() - 1) < 1e-6 and all(c["fun"](w) >= -1e-6 for c in cons)
    w = w / w.sum()
    return _result(w, mu.index, m_, S, rf, ok, "Convergence atteinte" if ok else f"Échec de l'optimiseur : {res.message}")
