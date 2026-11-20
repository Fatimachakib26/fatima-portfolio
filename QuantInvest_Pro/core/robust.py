"""
Estimateurs robustes.

- Covariance empirique : estimateur sans biais classique.
- Ledoit-Wolf (2004) : Σ̂ = (1 − δ)·S + δ·F, combinaison de la covariance
  empirique S et d'une cible structurée F (identité mise à l'échelle). Le
  coefficient δ ∈ [0, 1] est choisi pour minimiser l'erreur quadratique
  attendue : il réduit les erreurs d'estimation que l'optimiseur amplifie.
"""
from __future__ import annotations

import pandas as pd
from sklearn.covariance import LedoitWolf


def estimate_cov(returns: pd.DataFrame, method: str = "sample") -> tuple[pd.DataFrame, float | None]:
    """Covariance PÉRIODIQUE (non annualisée) et coefficient de rétrécissement."""
    if method == "sample":
        return returns.cov(), None
    if method == "ledoit_wolf":
        lw = LedoitWolf(assume_centered=False).fit(returns.to_numpy())
        # sklearn normalise par T ; on ramène à T−1 pour rester comparable à l'empirique
        t = len(returns)
        cov = pd.DataFrame(lw.covariance_ * t / (t - 1), index=returns.columns, columns=returns.columns)
        return cov, float(lw.shrinkage_)
    raise ValueError(f"Estimateur de covariance inconnu : {method}")
