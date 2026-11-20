"""
Profil et données fondamentales d'une action (yfinance Ticker.info).

Les champs manquants sont renvoyés à None (affichés « non disponible »).
Les réponses sont conservées sur disque avec leur date : en cas d'échec du
téléchargement, la dernière version connue est réutilisée et datée.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from config import CACHE_DIR

FIELDS = {
    "longName": "Nom", "sector": "Secteur", "industry": "Industrie", "country": "Pays", "marketCap": "Capitalisation",
    "currency": "Devise", "longBusinessSummary": "Description", "trailingPE": "PER (12 derniers mois)",
    "forwardPE": "PER prévisionnel", "dividendYield": "Rendement du dividende", "profitMargins": "Marge nette",
    "revenueGrowth": "Croissance du chiffre d'affaires", "returnOnEquity": "Rentabilité des capitaux propres",
    "mostRecentQuarter": "Dernier trimestre publié", "fullTimeEmployees": "Effectif",
}
SECTORS_FR = {"Technology": "Technologie", "Communication Services": "Services de communication",
              "Consumer Cyclical": "Consommation cyclique", "Consumer Defensive": "Consommation de base",
              "Financial Services": "Services financiers", "Healthcare": "Santé", "Energy": "Énergie",
              "Industrials": "Industrie", "Utilities": "Services publics", "Real Estate": "Immobilier",
              "Basic Materials": "Matériaux de base"}


def _cache_path(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "profiles.json"


def get_profile(ticker: str, fetcher=None, cache_dir: Path = CACHE_DIR) -> dict:
    """{champ: valeur ou None, '_source': ..., '_date': ...}."""
    path = _cache_path(Path(cache_dir))
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    try:
        if fetcher is None:
            import yfinance as yf
            info = yf.Ticker(ticker).info or {}
        else:
            info = fetcher(ticker)
        if not info or len(info) < 3:
            raise ValueError("réponse vide")
        prof = {k: info.get(k) for k in FIELDS}
        prof["_date"] = datetime.now().isoformat(timespec="minutes")
        prof["_source"] = "Yahoo Finance (yfinance, Ticker.info)"
        cache[ticker] = prof
        try:
            path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass
        return prof
    except Exception as exc:
        if ticker in cache:
            prof = dict(cache[ticker])
            prof["_source"] = f"Copie locale du {prof.get('_date', '?')[:10]} (Yahoo Finance indisponible : {exc})"
            return prof
        return {k: None for k in FIELDS} | {"_date": None, "_source": f"Non disponible ({exc})"}


def sector_fr(sector: str | None) -> str:
    return SECTORS_FR.get(sector, sector) if sector else "Non renseigné"
