"""
QuantInvest Pro — configuration centrale.

Toutes les valeurs par défaut de l'application sont définies ici, séparées du
code métier (core/) et de l'interface (pages/, components/). Les paramètres
modifiables par l'utilisateur sont regroupés dans la dataclass `AppParams`,
stockée dans st.session_state par app.py.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------- #
# Identité
# --------------------------------------------------------------------------- #
APP_NAME = "QuantInvest Pro"
TAGLINE = "Optimisation de portefeuille et analyse des risques"
VERSION = "1.0.0"
INSTITUTION = "EMSI — Finance quantitative avancée"

# --------------------------------------------------------------------------- #
# Chemins
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
CACHE_DIR = ROOT_DIR / "data" / "cache"
STYLE_PATH = ASSETS_DIR / "style.css"
LOGO_PATH = ASSETS_DIR / "logo.png"

# --------------------------------------------------------------------------- #
# Univers d'actifs proposés (l'utilisateur peut aussi saisir d'autres tickers)
# --------------------------------------------------------------------------- #
ASSET_UNIVERSE: dict[str, str] = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta Platforms",
    "TSLA": "Tesla",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "JNJ": "Johnson & Johnson",
    "XOM": "ExxonMobil",
    "KO": "Coca-Cola",
}
DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"]

# Benchmark : SPY (ETF, cours ajustés des dividendes) est cohérent avec les
# cours ajustés des actions. ^GSPC est un indice de prix sans dividendes :
# il sous-estime la performance réelle du marché (~1,3 %/an).
BENCHMARKS: dict[str, str] = {
    "SPY": "S&P 500 — ETF SPY (rendement total, recommandé)",
    "^GSPC": "S&P 500 — indice de prix (hors dividendes)",
}
DEFAULT_BENCHMARK = "SPY"

# --------------------------------------------------------------------------- #
# Fréquences : libellé -> (règle de rééchantillonnage pandas, périodes par an)
# None = données quotidiennes brutes (jours de cotation).
# --------------------------------------------------------------------------- #
FREQUENCIES: dict[str, tuple[str | None, int]] = {
    "Quotidienne": (None, 252),
    "Hebdomadaire": ("W-FRI", 52),
    "Mensuelle": ("ME", 12),
}

# --------------------------------------------------------------------------- #
# Méthodes
# --------------------------------------------------------------------------- #
COV_METHODS: dict[str, str] = {
    "sample": "Covariance empirique",
    "ledoit_wolf": "Ledoit-Wolf (shrinkage)",
}
OPTIMIZATION_OBJECTIVES: dict[str, str] = {
    "max_sharpe": "Sharpe maximal",
    "min_variance": "Variance minimale",
    "equal_weight": "Équipondéré (1/N)",
}
# Rééquilibrage exprimé en séances de bourse (≈ 21 par mois)
REBALANCING: dict[int, str] = {
    21: "Mensuel (21 séances)",
    63: "Trimestriel (63 séances)",
    126: "Semestriel (126 séances)",
    252: "Annuel (252 séances)",
}
# Analyse de sensibilité (fenêtres en séances × plafonds de poids)
SENSITIVITY_WINDOWS = [126, 252, 504, 756]
SENSITIVITY_CAPS = [0.20, 0.30, 0.40, 0.60, 1.00]
# Périodes de crise grisées sur les graphiques
CRISES = [
    ("Krach Covid", "2020-02-20", "2020-03-23"),
    ("Hausse des taux 2022", "2022-01-01", "2022-12-31"),
]
MIN_HISTORY_YEARS = 2      # en dessous : avertissement (estimation fragile)

# --------------------------------------------------------------------------- #
# Traitement des données
# --------------------------------------------------------------------------- #
FFILL_LIMIT = 3            # jours fériés : report maximal de la dernière valeur
MAX_MISSING_RATIO = 0.10   # au-delà, l'actif est exclu (historique insuffisant)
MIN_OBSERVATIONS = 60      # minimum d'observations communes pour estimer Σ
CACHE_TTL_SECONDS = 3600   # durée de vie du cache mémoire Streamlit
RANDOM_SEED = 42           # reproductibilité des simulations Monte-Carlo


@dataclass
class AppParams:
    """Paramètres modifiables par l'utilisateur (page Paramètres)."""

    tickers: list[str] = field(default_factory=lambda: list(DEFAULT_TICKERS))
    benchmark: str = DEFAULT_BENCHMARK
    start_date: date = date(2019, 1, 1)
    end_date: date = field(default_factory=date.today)
    frequency: str = "Quotidienne"
    risk_free_rate: float = 0.04          # taux annuel, ex. bons du Trésor US
    weight_min: float = 0.0               # pas de vente à découvert par défaut
    weight_max: float = 0.40              # plafond par actif (diversification imposée)
    split_date: date = date(2023, 12, 31) # fin de la période d'estimation
    n_simulations: int = 5000             # portefeuilles aléatoires (nuage)
    cov_method: str = "sample"
    objective: str = "max_sharpe"
    # Backtesting
    estimation_window: int = 252          # séances d'estimation glissante
    rebalance_days: int = 21              # séances entre deux rééquilibrages
    corr_window: int = 63                 # fenêtre de la corrélation glissante
    transaction_cost_bps: float = 10.0    # 10 points de base par unité de rotation
    initial_capital: float = 10_000.0

    def periods_per_year(self) -> int:
        return FREQUENCIES[self.frequency][1]

    def validate(self) -> list[str]:
        """Retourne la liste des erreurs de cohérence (vide si tout est valide)."""
        errors: list[str] = []
        n = len(self.tickers)
        if n < 2:
            errors.append("Sélectionnez au moins 2 actifs pour diversifier.")
        if self.start_date >= self.end_date:
            errors.append("La date de début doit précéder la date de fin.")
        if not 0.0 <= self.weight_min < self.weight_max <= 1.0:
            errors.append("Bornes de pondération invalides : 0 ≤ min < max ≤ 1.")
        if n >= 2 and self.weight_max * n < 1.0 - 1e-9:
            errors.append(
                f"Contraintes infaisables : {n} actifs × max {self.weight_max:.0%} < 100 %."
            )
        if n >= 2 and self.weight_min * n > 1.0 + 1e-9:
            errors.append(
                f"Contraintes infaisables : {n} actifs × min {self.weight_min:.0%} > 100 %."
            )
        if not self.start_date < self.split_date < self.end_date:
            errors.append("La date de séparation doit se situer strictement entre le début et la fin.")
        if not -0.05 <= self.risk_free_rate <= 0.25:
            errors.append("Taux sans risque hors de la plage plausible [-5 %, 25 %].")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Palette (dupliquée dans style.css sous forme de variables CSS)
# --------------------------------------------------------------------------- #
COLORS = {
    "bg0": "#07071A",
    "bg1": "#0F1030",
    "card": "rgba(255,255,255,0.04)",
    "border": "rgba(167,139,250,0.18)",
    "text": "#E6E6F5",
    "muted": "#8E8FB5",
    "grid": "rgba(142,143,181,0.12)",
    "violet": "#8B5CF6",
    "violet2": "#A855F7",
    "blue": "#3B82F6",
    "cyan": "#22D3EE",
    "pink": "#EC4899",
    "amber": "#F59E0B",
    "up": "#22C55E",
    "down": "#F43F5E",
}
# Ordre des séries : portefeuille optimal, benchmark, équipondéré, puis actifs
SERIES_COLORS = [
    "#A855F7", "#22D3EE", "#F59E0B", "#3B82F6",
    "#EC4899", "#22C55E", "#818CF8", "#F97316",
    "#14B8A6", "#E879F9", "#60A5FA", "#FACC15",
]
