"""Formats français : virgule décimale, espace fine insécable avant « % »."""
from __future__ import annotations

import math

import pandas as pd

NNBSP = " "  # espace fine insécable (typographie française)

# Indicateurs exprimés en pourcentage (les autres sont des ratios ou des comptes)
PCT_METRICS = {
    "Rendement annualisé", "Volatilité annualisée", "Drawdown maximal", "Rendement cumulé",
    "VaR 95 % historique", "CVaR 95 %", "VaR 95 % paramétrique", "Rotation annuelle",
}

METRIC_HELP = {
    "Rendement annualisé": "Taux de croissance annuel composé : le rendement constant par an qui aurait donné le même résultat final.",
    "Volatilité annualisée": "Écart-type des rendements ramené à l'année (× √252) : l'amplitude habituelle des variations.",
    "Sharpe": "Rendement en excès du taux sans risque par unité de volatilité : plus il est élevé, mieux le risque est rémunéré.",
    "Sortino": "Comme le Sharpe, mais seule la volatilité des baisses (sous le taux sans risque) est pénalisée.",
    "Calmar": "Rendement annualisé divisé par la pire baisse subie : le gain obtenu pour chaque point de perte maximale.",
    "Drawdown maximal": "Pire baisse depuis un plus haut historique : la perte maximale d'un investisseur entré au mauvais moment.",
    "Rendement cumulé": "Gain ou perte total sur toute la période.",
    "VaR 95 % historique": "Perte sur 1 jour qui n'a été dépassée que 5 % des jours (5e centile des rendements observés).",
    "CVaR 95 %": "Perte moyenne les 5 % de jours les plus mauvais : la gravité des pertes au-delà de la VaR.",
    "VaR 95 % paramétrique": "VaR calculée en supposant des rendements de loi normale (moyenne et écart-type) : plus simple, souvent trop optimiste.",
    "Rotation annuelle": "Part du portefeuille échangée chaque année : 100 % = tout le portefeuille est renouvelé une fois par an.",
    "Nb effectif de titres": "1 / Σw² : nombre d'actifs « équivalents » réellement détenus (6 pour le 1/N à 6 actifs).",
    "Sharpe annoncé (moyen)": "Sharpe promis par l'optimiseur au moment de chaque décision, calculé sur la fenêtre d'estimation.",
}


def num(x: float, d: int = 2, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    s = f"{x:+,.{d}f}" if signed else f"{x:,.{d}f}"
    return s.replace(",", NNBSP).replace(".", ",").replace("-", "−")


def pct(x: float, d: int = 2, signed: bool = False) -> str:
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else num(100 * x, d, signed) + NNBSP + "%"


def format_metrics(tab: pd.DataFrame, d: int = 2) -> pd.DataFrame:
    """Tableau d'indicateurs → chaînes au format français (pour l'affichage)."""
    out = pd.DataFrame(index=tab.index)
    for col in tab.columns:
        if col == "Observations":
            out[col] = tab[col].map(lambda v: num(v, 0))
        elif col in PCT_METRICS:
            out[col] = tab[col].map(lambda v: pct(v, d))
        else:
            out[col] = tab[col].map(lambda v: num(v, d))
    return out


def weights_table(weights: dict[str, pd.Series]) -> pd.DataFrame:
    return pd.DataFrame({k: v.map(lambda x: pct(x, 1)) for k, v in weights.items()})
