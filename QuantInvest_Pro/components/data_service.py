"""
Pont entre Streamlit et le moteur de données (core/).

- Mise en cache mémoire (st.cache_data, TTL 1 h) pour éviter de
  retélécharger à chaque interaction.
- Le bouton « Actualiser » incrémente un compteur qui fait partie de la
  clé de cache : il force un nouveau téléchargement.
- Le résultat est rangé dans st.session_state["market"] et lu par toutes
  les pages ; le statut (live / cache / erreur) alimente la barre supérieure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import streamlit as st

from components.kpi_cards import banner
from config import CACHE_TTL_SECONDS, FREQUENCIES, MIN_HISTORY_YEARS, AppParams
from core.data_loader import MarketData, load_prices
from core.preprocessing import CleanResult, DataQualityError, clean_prices, mixed_currencies, resample_prices


@dataclass
class MarketBundle:
    """Tout ce dont les pages ont besoin, prêt à l'emploi."""

    raw: MarketData
    clean: CleanResult | None = None
    error: str | None = None
    assets: list[str] = field(default_factory=list)     # actifs retenus (hors benchmark)
    benchmark: str | None = None                         # None si benchmark indisponible
    freq_prices: pd.DataFrame | None = None              # prix à la fréquence choisie
    periods_per_year: int = 252

    @property
    def ok(self) -> bool:
        return self.clean is not None and len(self.assets) >= 1

    @property
    def prices(self) -> pd.DataFrame:
        """Prix des actifs retenus (fréquence choisie)."""
        return self.freq_prices[self.assets]

    @property
    def benchmark_prices(self) -> pd.Series | None:
        return self.freq_prices[self.benchmark] if self.benchmark else None

    @property
    def daily_prices(self) -> pd.DataFrame:
        """Prix quotidiens des actifs retenus (backtests en séances)."""
        return self.clean.prices[self.assets]

    @property
    def history_years(self) -> float:
        return (self.clean.end - self.clean.start).days / 365.25 if self.clean is not None else 0.0


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def _cached_load(tickers: tuple[str, ...], start: date, end: date, nonce: int) -> MarketData:
    # `nonce` ne sert qu'à invalider le cache quand l'utilisateur actualise.
    return load_prices(list(tickers), start, end)


def request_refresh() -> None:
    """Callback du bouton Actualiser (exécuté AVANT la réexécution du script)."""
    st.session_state["refresh_nonce"] = st.session_state.get("refresh_nonce", 0) + 1


def load_market_data(params: AppParams) -> MarketBundle:
    universe = tuple(dict.fromkeys([*params.tickers, params.benchmark]))
    nonce = st.session_state.get("refresh_nonce", 0)
    with st.spinner("Connexion à Yahoo Finance…"):
        try:
            raw = _cached_load(universe, params.start_date, params.end_date, nonce)
        except Exception as exc:  # filet de sécurité : l'application reste utilisable
            raw = MarketData(prices=pd.DataFrame(), source={t: "missing" for t in universe},
                             messages=[f"Erreur inattendue lors du téléchargement : {exc}"])

    st.session_state["data_status"] = {"state": raw.status, "fetched_at": raw.as_of}
    bundle = MarketBundle(raw=raw)
    try:
        clean = clean_prices(raw.prices)
        bundle.clean = clean
        rule, bundle.periods_per_year = FREQUENCIES[params.frequency]
        bundle.freq_prices = resample_prices(clean.prices, rule)
    except DataQualityError as exc:
        bundle.error = str(exc)
        return bundle

    cols = set(clean.prices.columns)
    bundle.assets = [t for t in params.tickers if t in cols]
    bundle.benchmark = params.benchmark if params.benchmark in cols else None
    if len(bundle.assets) < 2:
        bundle.error = "Moins de 2 actifs disposent de données exploitables : optimisation impossible."
    return bundle


def source_text(bundle: MarketBundle) -> str:
    """Source complète, avec la date de téléchargement des données utilisées."""
    from core.trace import SOURCE_YAHOO
    stamp = bundle.raw.as_of
    return SOURCE_YAHOO + (f", téléchargés le {stamp:%d/%m/%Y à %H:%M}" if stamp else "")


def render_data_alerts(bundle: MarketBundle) -> None:
    """Bandeaux d'information sur la qualité et l'origine des données."""
    raw = bundle.raw
    if raw.status == "error":
        banner("Impossible d'obtenir des données (ni Yahoo Finance, ni cache local). "
               "Vérifiez votre connexion Internet puis cliquez sur <b>Actualiser</b>.", "error", "⛔")
    elif raw.from_cache:
        oldest = min(raw.fetched_at[t] for t in raw.from_cache)
        banner(f"Yahoo Finance indisponible pour <b>{', '.join(raw.from_cache)}</b> : utilisation des "
               f"dernières données valides conservées (récupérées le {oldest:%d/%m/%Y à %H:%M}). "
               "Cliquez sur <b>Actualiser</b> pour réessayer.", "warn", "🟡")
    if raw.failed and raw.status != "error":
        banner("Tickers introuvables ou sans données : <b>" + ", ".join(raw.failed) + "</b>. "
               "Vérifiez leur orthographe Yahoo (ex. MC.PA pour LVMH).", "error", "⚠️")
    if bundle.clean is not None and bundle.clean.excluded:
        details = "; ".join(f"<b>{t}</b> — {r}" for t, r in bundle.clean.excluded.items())
        banner("Actifs exclus du calcul : " + details, "warn", "🧹")
    if bundle.clean is not None and not bundle.benchmark:
        banner("Indice de référence indisponible : les comparaisons avec le S&amp;P 500 sont désactivées.", "warn", "📉")
    currencies = mixed_currencies({t: c for t, c in raw.currencies.items() if t in bundle.assets})
    if len(currencies) > 1:
        banner("Devises multiples détectées (" + ", ".join(sorted(currencies)) + ") : les rendements sont "
               "calculés dans la devise de chaque actif, sans conversion de change.", "warn", "💱")
    if bundle.clean is not None and bundle.history_years < MIN_HISTORY_YEARS:
        banner(f"Historique commun de seulement {bundle.history_years:.1f} an(s)".replace(".", ",")
               + f" (minimum conseillé : {MIN_HISTORY_YEARS} ans) : les estimations de μ et Σ sont fragiles "
               "et la période de test sera courte.", "warn", "⏳")
    if bundle.error and raw.status != "error":  # évite un doublon avec le bandeau ci-dessus
        banner(bundle.error, "error", "⛔")
