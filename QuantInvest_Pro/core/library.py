"""
Bibliothèque de portefeuilles.

Chaque portefeuille conserve ses poids ET les paramètres qui l'ont produit
(période d'estimation, estimateur, taux sans risque, contraintes) : on peut
toujours expliquer d'où il vient. Format sérialisable en JSON.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime

import pandas as pd

from core.optimization import EQUAL, MAX_SHARPE, MIN_VAR, equal_weight, max_sharpe, min_variance, risk_parity
from core.portfolio import buy_and_hold_returns
from core.returns import Estimates

FIXED_COLORS = {
    MIN_VAR: "#22D3EE", MAX_SHARPE: "#A855F7", EQUAL: "#F59E0B",
    "Variance minimale (Ledoit-Wolf)": "#14B8A6", "Sharpe maximal (Ledoit-Wolf)": "#EC4899",
    "Parité de risque": "#22C55E", "SPY": "#E2E8F0",
}
CUSTOM_PALETTE = ["#60A5FA", "#F97316", "#E879F9", "#FACC15", "#818CF8", "#2DD4BF", "#FB7185", "#A3E635"]
TYPES = {"automatique": "Optimisé automatiquement", "personnalise": "Construit à la main",
         "cible": "Cible sur la frontière", "reference": "Indice de référence", "frontiere": "Point de la frontière"}


@dataclass
class Entry:
    nom: str
    poids: dict[str, float]
    type: str
    description: str
    couleur: str
    date_creation: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    parametres: dict = field(default_factory=dict)

    @property
    def weights(self) -> pd.Series:
        return pd.Series(self.poids, dtype=float)


def params_dict(est: Estimates, rf: float, lo: float, hi: float, objectif: str) -> dict:
    return {"objectif": objectif, "periode_estimation": [f"{est.start:%Y-%m-%d}", f"{est.end:%Y-%m-%d}"],
            "observations": est.n_obs, "estimateur": est.method, "taux_sans_risque": rf, "poids_min": lo,
            "poids_max": hi}


def automatic(est_sample: Estimates, est_lw: Estimates, rf: float, lo: float, hi: float,
              benchmark: str | None = "SPY") -> dict[str, Entry]:
    """Portefeuilles automatiques, tous estimés sur la même période d'estimation."""
    hi_ = max(hi, 1 / len(est_sample.mu))
    specs = [
        (MIN_VAR, min_variance(est_sample.mu, est_sample.cov, lo, hi_, rf).weights, est_sample, "min wᵀΣw, covariance empirique"),
        (MAX_SHARPE, max_sharpe(est_sample.mu, est_sample.cov, rf, lo, hi_).weights, est_sample, "max Sharpe, covariance empirique"),
        (EQUAL, equal_weight(est_sample.mu, est_sample.cov, rf).weights, est_sample, "1/N : aucune estimation"),
        ("Variance minimale (Ledoit-Wolf)", min_variance(est_lw.mu, est_lw.cov, lo, hi_, rf).weights, est_lw,
         "min wᵀΣw, covariance de Ledoit-Wolf"),
        ("Sharpe maximal (Ledoit-Wolf)", max_sharpe(est_lw.mu, est_lw.cov, rf, lo, hi_).weights, est_lw,
         "max Sharpe, covariance de Ledoit-Wolf"),
        ("Parité de risque", risk_parity(est_sample.cov), est_sample, "contributions au risque égales (sans plafond)"),
    ]
    out = {}
    for name, w, est, desc in specs:
        objectif = {"Parité de risque": "parite_risque", EQUAL: "equipondere"}.get(name, "optimisation")
        out[name] = Entry(name, {k: float(v) for k, v in w.items()}, "automatique", desc, FIXED_COLORS[name],
                          parametres=params_dict(est, rf, lo, hi_ if name != "Parité de risque" else 1.0, objectif))
    if benchmark:
        out[benchmark] = Entry(benchmark, {benchmark: 1.0}, "reference", "Indice de référence (ETF S&P 500)",
                               FIXED_COLORS.get(benchmark, "#E2E8F0"), parametres={"objectif": "reference"})
    return out


def validate(weights: dict[str, float], lo: float, hi: float, tol: float = 1e-6) -> list[str]:
    errs = []
    total = sum(weights.values())
    if abs(total - 1) > tol:
        errs.append(f"La somme des poids vaut {total:.2%} au lieu de 100 % (utilisez « Normaliser à 100 % »).".replace(".", ",", 1))
    for k, v in weights.items():
        if v < lo - tol or v > hi + tol:
            errs.append(f"{k} : {v:.1%} hors des bornes [{lo:.0%} ; {hi:.0%}].")
    return errs


def normalize(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Impossible de normaliser : tous les poids sont nuls.")
    return {k: v / total for k, v in weights.items()}


def next_color(library: dict[str, Entry]) -> str:
    used = {e.couleur for e in library.values()}
    return next((c for c in CUSTOM_PALETTE if c not in used), CUSTOM_PALETTE[len(library) % len(CUSTOM_PALETTE)])


def duplicate(library: dict[str, Entry], name: str) -> str:
    base, i = f"{name} (copie)", 2
    new = base
    while new in library:
        new, i = f"{base} {i}", i + 1
    src = library[name]
    library[new] = Entry(new, dict(src.poids), "personnalise", f"Copie de « {name} »", next_color(library),
                         parametres=dict(src.parametres))
    return new


def rename(library: dict[str, Entry], old: str, new: str) -> None:
    if not new.strip():
        raise ValueError("Le nouveau nom est vide.")
    if new in library:
        raise ValueError(f"« {new} » existe déjà.")
    e = library.pop(old)
    e.nom = new
    library[new] = e


def to_json(library: dict[str, Entry]) -> str:
    return json.dumps({k: asdict(v) for k, v in library.items()}, ensure_ascii=False, indent=2)


def from_json(text: str) -> dict[str, Entry]:
    raw = json.loads(text)
    out = {}
    for k, v in raw.items():
        if not isinstance(v.get("poids"), dict) or not v["poids"]:
            raise ValueError(f"Portefeuille « {k} » invalide : poids manquants.")
        out[k] = Entry(**{f: v[f] for f in ("nom", "poids", "type", "description", "couleur")},
                       date_creation=v.get("date_creation", datetime.now().isoformat(timespec="seconds")),
                       parametres=v.get("parametres", {}))
    return out


def entry_returns(entry: Entry, asset_returns: pd.DataFrame, benchmark_returns: pd.Series | None) -> pd.Series:
    """Rendements d'un portefeuille sur les dates de `asset_returns` : achat au premier jour
    aux poids de la bibliothèque, puis conservation (poids figés, aucune réestimation)."""
    w = entry.weights
    if entry.type == "reference":
        if benchmark_returns is None:
            raise ValueError("Indice de référence indisponible.")
        return benchmark_returns.loc[asset_returns.index].rename(entry.nom)
    missing = [a for a in w.index if a not in asset_returns.columns]
    if missing:
        raise ValueError(f"Actifs absents des données chargées : {', '.join(missing)}.")
    return buy_and_hold_returns(asset_returns, w).rename(entry.nom)
