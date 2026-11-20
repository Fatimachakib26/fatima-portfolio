"""
Nettoyage et synchronisation des séries de prix.

Règles (documentées dans la page Méthodologie) :
1. Dates normalisées (sans fuseau horaire), triées, sans doublon.
2. Prix non positifs ou infinis → valeur manquante (erreur de source).
3. Actif exclu si sa part de valeurs manquantes dépasse le seuil
   (historique trop court ou trop lacunaire pour estimer Σ).
4. Report de la dernière valeur connue limité à `ffill_limit` séances
   (jours fériés propres à une place boursière). Jamais de report vers
   l'arrière : on n'utilise pas une information future.
5. Conservation des seules dates où TOUS les actifs ont un prix
   (historique commun, exigé par la fiche du projet).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config import FFILL_LIMIT, MAX_MISSING_RATIO, MIN_OBSERVATIONS


class DataQualityError(ValueError):
    """Données insuffisantes pour une analyse fiable."""


@dataclass
class CleanResult:
    prices: pd.DataFrame                      # prix propres, dates communes
    quality: pd.DataFrame                     # rapport de qualité par actif
    excluded: dict[str, str] = field(default_factory=dict)  # ticker -> raison

    @property
    def start(self) -> pd.Timestamp:
        return self.prices.index[0]

    @property
    def end(self) -> pd.Timestamp:
        return self.prices.index[-1]

    @property
    def n_obs(self) -> int:
        return len(self.prices)


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    idx = pd.to_datetime(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df.index.name = "Date"
    return df


def clean_prices(
    raw: pd.DataFrame,
    *,
    ffill_limit: int = FFILL_LIMIT,
    max_missing_ratio: float = MAX_MISSING_RATIO,
    min_obs: int = MIN_OBSERVATIONS,
) -> CleanResult:
    """Applique les règles 1 à 5 et retourne les prix + un rapport de qualité."""
    if raw is None or raw.empty or raw.shape[1] == 0:
        raise DataQualityError("Aucune série de prix disponible.")

    df = _normalize_index(raw).apply(pd.to_numeric, errors="coerce")
    invalid = (~np.isfinite(df) | (df <= 0)) & df.notna()
    df = df.mask(invalid)
    df = df.dropna(how="all")  # jours sans aucune cotation
    if df.empty:
        raise DataQualityError("Toutes les valeurs de prix sont manquantes.")

    rows = []
    excluded: dict[str, str] = {}
    for t in df.columns:
        s = df[t]
        n_missing = int(s.isna().sum())
        ratio = n_missing / len(s)
        if s.notna().sum() == 0:
            excluded[t] = "aucune donnée"
        elif ratio > max_missing_ratio:
            excluded[t] = (f"{ratio:.0%} de valeurs manquantes (historique commençant le "
                           f"{s.first_valid_index():%d/%m/%Y})")
        rows.append({
            "Actif": t,
            "Première date": s.first_valid_index(),
            "Dernière date": s.last_valid_index(),
            "Observations": int(s.notna().sum()),
            "Manquantes": n_missing,
            "% manquantes": ratio,
            "Prix invalides": int(invalid[t].sum()),
        })

    kept = [t for t in df.columns if t not in excluded]
    if len(kept) == 0:
        raise DataQualityError("Tous les actifs ont été exclus pour données insuffisantes.")

    before_fill = df[kept]
    filled = before_fill.ffill(limit=ffill_limit)
    n_filled = (filled.notna() & before_fill.isna()).sum()
    common = filled.dropna(how="any")

    quality = pd.DataFrame(rows).set_index("Actif")
    quality["Valeurs complétées"] = n_filled.reindex(quality.index).fillna(0).astype(int)
    quality["Statut"] = ["Exclu : " + excluded[t] if t in excluded else "Retenu" for t in quality.index]

    if len(common) < min_obs:
        raise DataQualityError(
            f"Seulement {len(common)} dates communes (minimum {min_obs}). "
            "Élargissez la période ou retirez l'actif à l'historique le plus court."
        )
    return CleanResult(prices=common, quality=quality, excluded=excluded)


def resample_prices(prices: pd.DataFrame, rule: str | None) -> pd.DataFrame:
    """Change la fréquence (dernier prix de chaque période). None = inchangé."""
    if rule is None:
        return prices
    out = prices.resample(rule).last().dropna(how="any")
    out.index.name = "Date"
    return out


def mixed_currencies(currencies: dict[str, str | None]) -> set[str]:
    """Ensemble des devises distinctes connues (alerte si plus d'une)."""
    return {c for c in currencies.values() if c}
