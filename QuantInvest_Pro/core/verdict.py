"""
Verdict automatique : synthèse en une phrase des résultats hors échantillon,
générée uniquement à partir des chiffres calculés.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.optimization import EQUAL, MAX_SHARPE
from core.stats_tests import memmel_test

ALPHA = 0.05


def fr_num(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def fr_pct(x: float, d: int = 1) -> str:
    return fr_num(100 * x, d) + " %"


@dataclass
class Verdict:
    sentence: str
    best_name: str
    best_sharpe: float
    worst_name: str
    worst_drawdown: float
    announced: float
    realized: float
    p_value: float
    significant: bool

    @property
    def sharpe_gap(self) -> float:
        return self.realized - self.announced


def build_verdict(returns_test: pd.DataFrame, metrics_test: pd.DataFrame, announced_sharpe: float,
                  rf_periodic: float, start: pd.Timestamp, end: pd.Timestamp) -> Verdict:
    """returns_test : rendements quotidiens hors échantillon, une colonne par portefeuille."""
    t = memmel_test(returns_test[MAX_SHARPE], returns_test[EQUAL], rf_periodic)
    sr_ms, sr_eq = metrics_test.loc[MAX_SHARPE, "Sharpe"], metrics_test.loc[EQUAL, "Sharpe"]
    significant = t["p_value"] < ALPHA
    if sr_ms > sr_eq:
        comp = "il fait mieux que le 1/N" + (", et l'écart est statistiquement significatif" if significant
                                             else ", mais l'écart n'est pas statistiquement significatif")
    else:
        comp = "il ne fait pas mieux que le 1/N" + (" et l'écart est statistiquement significatif" if significant
                                                    else " ; l'écart n'est pas statistiquement significatif")
    sentence = (
        f"Hors échantillon ({start:%d/%m/%Y} – {end:%d/%m/%Y}), le portefeuille de Sharpe maximal obtient un "
        f"Sharpe de {fr_num(sr_ms)} contre {fr_num(sr_eq)} pour le 1/N : {comp} "
        f"(test de Memmel, p = {fr_num(t['p_value'], 3)}). "
        f"L'optimiseur annonçait {fr_num(announced_sharpe)} sur la période d'estimation : "
        + ("la performance annoncée a été tenue." if sr_ms >= announced_sharpe
           else f"le Sharpe réalisé est inférieur de {fr_num(announced_sharpe - sr_ms)} à l'annonce.")
    )
    best = metrics_test["Sharpe"].idxmax()
    worst = metrics_test["Drawdown maximal"].idxmin()
    return Verdict(sentence, best, float(metrics_test.loc[best, "Sharpe"]), worst,
                   float(metrics_test.loc[worst, "Drawdown maximal"]), float(announced_sharpe),
                   float(sr_ms), t["p_value"], significant)
