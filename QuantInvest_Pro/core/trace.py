"""
Traçabilité des calculs.

Chaque indicateur est renvoyé sous la forme d'un objet `Resultat` qui contient,
en plus de sa valeur : sa définition, sa formule (LaTeX), les données d'entrée
avec leur valeur, le calcul détaillé avec les vrais nombres, la source des
données et la période utilisée. L'interface peut ainsi répondre, pour chaque
chiffre affiché, à la question « d'où vient ce chiffre ? ».
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

NNBSP = " "
SOURCE_YAHOO = "Yahoo Finance via yfinance, cours de clôture ajustés (dividendes et divisions)"


def fr_num(x: float, d: int = 2, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "non disponible"
    s = f"{x:+,.{d}f}" if signed else f"{x:,.{d}f}"
    return s.replace(",", NNBSP).replace(".", ",").replace("-", "−")


def fr_val(x: float, unite: str, d: int | None = None) -> str:
    """Format français selon l'unité : pct, ratio, nombre, seances."""
    if unite == "pct":
        s = fr_num(100 * x, 2 if d is None else d)
        return s if s == "non disponible" else s + NNBSP + "%"
    if unite == "seances":
        return fr_num(x, 0) + " séances"
    if unite == "nombre":
        return fr_num(x, 2 if d is None else d)
    return fr_num(x, 2 if d is None else d)


@dataclass
class Entree:
    nom: str
    valeur: float
    unite: str = "ratio"           # pct, ratio, nombre, seances
    cle: str = ""                  # identifiant utilisé par le recalcul

    @property
    def texte(self) -> str:
        return fr_val(self.valeur, self.unite, 4 if self.unite == "ratio" else None)


@dataclass
class Resultat:
    cle: str
    nom: str
    valeur: float
    unite: str
    definition: str
    formule: str                   # LaTeX
    entrees: list[Entree] = field(default_factory=list)
    etapes: list[str] = field(default_factory=list)
    source: str = SOURCE_YAHOO
    debut: pd.Timestamp | None = None
    fin: pd.Timestamp | None = None
    n_obs: int = 0
    lecture: str = ""              # grille de lecture
    limites: str = ""
    sujet: str = ""                # portefeuille ou actif concerné
    donnees: pd.DataFrame | None = None   # lignes utilisées (affichables, exportables)

    @property
    def texte(self) -> str:
        return fr_val(self.valeur, self.unite)

    @property
    def periode(self) -> str:
        if self.debut is None:
            return "non précisée"
        return f"{self.debut:%d/%m/%Y} → {self.fin:%d/%m/%Y} ({fr_num(self.n_obs, 0)} observations)"

    def entree(self, cle: str) -> float:
        for e in self.entrees:
            if e.cle == cle:
                return e.valeur
        raise KeyError(cle)

    def as_dict(self) -> dict:
        """Résumé exportable (JSON, CSV)."""
        return {"indicateur": self.nom, "sujet": self.sujet, "valeur": self.valeur, "unite": self.unite,
                "periode": self.periode, "source": self.source, "calcul": " | ".join(self.etapes)}
