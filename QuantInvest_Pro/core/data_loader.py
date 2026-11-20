"""
Collecte des données de marché (Yahoo Finance via yfinance).

Principes :
- Prix de clôture AJUSTÉS (auto_adjust=True) : dividendes et splits sont
  intégrés, ce qui rend les rendements comparables entre actifs et avec
  le benchmark SPY. (La colonne « Adj Close » des scripts du cours
  n'existe plus dans yfinance ≥ 0.2.51.)
- Aucun téléchargement ne fait planter l'application : un ticker en échec
  est retenté une fois, puis remplacé par la dernière version valide
  conservée sur disque (cache Parquet), avec sa date de récupération.
- Rien n'est inventé : sans données réelles ni cache, le ticker est
  déclaré en échec.

Ce module n'importe pas Streamlit : il est testable avec pytest.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

import pandas as pd

from config import CACHE_DIR

log = logging.getLogger(__name__)

Downloader = Callable[[list[str], date, date], pd.DataFrame]
CurrencyFn = Callable[[str], "str | None"]

LIVE, CACHE, MISSING = "live", "cache", "missing"


@dataclass
class MarketData:
    """Résultat d'un chargement : prix bruts + traçabilité de leur origine."""

    prices: pd.DataFrame                                   # index = dates, colonnes = tickers
    source: dict[str, str] = field(default_factory=dict)   # ticker -> live | cache | missing
    fetched_at: dict[str, datetime] = field(default_factory=dict)
    currencies: dict[str, str | None] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)

    @property
    def failed(self) -> list[str]:
        return [t for t, s in self.source.items() if s == MISSING]

    @property
    def from_cache(self) -> list[str]:
        return [t for t, s in self.source.items() if s == CACHE]

    @property
    def status(self) -> str:
        """État global affiché dans la barre supérieure."""
        if not self.source or all(s == MISSING for s in self.source.values()):
            return "error"
        if any(s != LIVE for s in self.source.values()):
            return "cache"
        return "live"

    @property
    def as_of(self) -> datetime | None:
        """Date de récupération la plus ancienne parmi les données utilisées."""
        stamps = [self.fetched_at[t] for t, s in self.source.items() if s != MISSING and t in self.fetched_at]
        return min(stamps) if stamps else None


# --------------------------------------------------------------------------- #
# Téléchargement Yahoo Finance
# --------------------------------------------------------------------------- #
def extract_close(raw: pd.DataFrame | None, tickers: list[str]) -> pd.DataFrame:
    """Extrait les prix de clôture d'un résultat yf.download, quel que soit
    son format (colonnes simples ou MultiIndex (champ, ticker))."""
    if raw is None or raw.empty:
        return pd.DataFrame(columns=tickers, dtype=float)
    if isinstance(raw.columns, pd.MultiIndex):
        fields = raw.columns.get_level_values(0)
        if "Close" in fields:
            close = raw["Close"]
        else:  # group_by="ticker" : (ticker, champ)
            close = raw.xs("Close", axis=1, level=1)
    else:
        close = raw[["Close"]].rename(columns={"Close": tickers[0]})
    close = close.reindex(columns=tickers).astype(float)
    close.columns.name = None
    return close


def yahoo_download(tickers: list[str], start: date, end: date) -> pd.DataFrame:
    """Téléchargement groupé. `end` est inclusif ici (yfinance l'exclut)."""
    import yfinance as yf  # import local : les tests n'en ont pas besoin

    raw = yf.download(
        tickers=tickers,
        start=start,
        end=end + timedelta(days=1),
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=True,
        group_by="column",
        multi_level_index=True,
        timeout=10,
    )
    return extract_close(raw, tickers)


def yahoo_currency(ticker: str) -> str | None:
    """Devise de cotation (USD, EUR, MAD…). None si indisponible."""
    try:
        import yfinance as yf

        return yf.Ticker(ticker).fast_info["currency"]
    except Exception as exc:  # réseau, ticker inconnu, champ absent
        log.warning("Devise indisponible pour %s : %s", ticker, exc)
        return None


# --------------------------------------------------------------------------- #
# Cache disque : un fichier Parquet par ticker + métadonnées JSON
# --------------------------------------------------------------------------- #
class PriceCache:
    def __init__(self, directory: Path = CACHE_DIR):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.dir / "meta.json"

    def _file(self, ticker: str) -> Path:
        return self.dir / (re.sub(r"[^A-Za-z0-9._-]", "_", ticker) + ".parquet")

    def _meta(self) -> dict:
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write_meta(self, meta: dict) -> None:
        self.meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    def save(self, ticker: str, series: pd.Series, fetched_at: datetime, currency: str | None) -> None:
        """Fusionne la nouvelle série avec l'historique déjà conservé."""
        series = series.dropna()
        if series.empty:
            return
        old = self.load_series(ticker)
        merged = series.combine_first(old) if old is not None else series  # le neuf prime
        merged.sort_index().rename("close").to_frame().to_parquet(self._file(ticker))
        meta = self._meta()
        meta[ticker] = {"fetched_at": fetched_at.isoformat(timespec="seconds"),
                        "currency": currency or meta.get(ticker, {}).get("currency")}
        self._write_meta(meta)

    def load_series(self, ticker: str) -> pd.Series | None:
        path = self._file(ticker)
        if not path.exists():
            return None
        try:
            s = pd.read_parquet(path)["close"]
        except Exception as exc:  # fichier corrompu : on l'ignore
            log.warning("Cache illisible pour %s : %s", ticker, exc)
            return None
        s.index = pd.to_datetime(s.index)
        return s.rename(ticker)

    def info(self, ticker: str) -> tuple[datetime | None, str | None]:
        entry = self._meta().get(ticker, {})
        stamp = entry.get("fetched_at")
        return (datetime.fromisoformat(stamp) if stamp else None, entry.get("currency"))


# --------------------------------------------------------------------------- #
# Point d'entrée
# --------------------------------------------------------------------------- #
def load_prices(
    tickers: list[str],
    start: date,
    end: date,
    *,
    cache_dir: Path = CACHE_DIR,
    downloader: Downloader = yahoo_download,
    currency_fn: CurrencyFn = yahoo_currency,
    retry_delay: float = 1.0,
    now: Callable[[], datetime] = datetime.now,
) -> MarketData:
    """Télécharge les prix ajustés de `tickers` sur [start, end].

    Ordre de priorité par ticker : téléchargement groupé → nouvelle tentative
    individuelle → cache disque → échec déclaré.
    """
    tickers = list(dict.fromkeys(t.strip().upper() for t in tickers if t and t.strip()))
    cache = PriceCache(cache_dir)
    md = MarketData(prices=pd.DataFrame(dtype=float))
    series: dict[str, pd.Series] = {}

    # 1. Téléchargement groupé (rapide, une seule requête)
    try:
        batch = downloader(tickers, start, end)
    except Exception as exc:
        md.messages.append(f"Téléchargement Yahoo Finance impossible : {exc}")
        batch = pd.DataFrame(columns=tickers, dtype=float)

    stamp = now()
    pending = []
    for t in tickers:
        s = batch[t].dropna() if t in batch.columns else pd.Series(dtype=float)
        if s.empty:
            pending.append(t)
        else:
            series[t] = s
            md.source[t], md.fetched_at[t] = LIVE, stamp

    # 2. Nouvelle tentative pour les tickers en échec. Si TOUT le lot a échoué,
    #    c'est probablement une coupure réseau : une seule tentative groupée
    #    suffit (inutile d'attendre un délai d'expiration par ticker).
    if pending:
        groups = [pending[:]] if len(pending) == len(tickers) else [[t] for t in pending]
        for group in groups:
            time.sleep(retry_delay)
            try:
                retry = downloader(group, start, end)
            except Exception:
                continue
            for t in group:
                s = retry[t].dropna() if t in retry.columns else pd.Series(dtype=float)
                if not s.empty:
                    series[t] = s
                    md.source[t], md.fetched_at[t] = LIVE, now()
                    pending.remove(t)

    # 3. Repli sur le cache disque (dernières données valides connues)
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    for t in pending:
        cached = cache.load_series(t)
        cached = cached.loc[lo:hi] if cached is not None else None
        fetched, currency = cache.info(t)
        if cached is not None and not cached.empty:
            series[t] = cached
            md.source[t], md.fetched_at[t] = CACHE, fetched or now()
            md.currencies[t] = currency
            md.messages.append(
                f"{t} : Yahoo Finance indisponible, utilisation des données en cache"
                f" du {md.fetched_at[t]:%d/%m/%Y %H:%M}."
            )
        else:
            md.source[t] = MISSING
            md.messages.append(f"{t} : aucune donnée téléchargée et aucun cache disponible.")

    # 4. Devises + sauvegarde des séries fraîches dans le cache
    for t in tickers:
        if md.source.get(t) != LIVE:
            continue
        cached_currency = cache.info(t)[1]
        md.currencies[t] = cached_currency or currency_fn(t)
        try:
            cache.save(t, series[t], md.fetched_at[t], md.currencies[t])
        except Exception as exc:  # disque plein, droits… : non bloquant
            log.warning("Écriture du cache impossible pour %s : %s", t, exc)

    if series:
        md.prices = pd.concat([series[t].rename(t) for t in tickers if t in series], axis=1)
        md.prices.index = pd.to_datetime(md.prices.index)
    return md
