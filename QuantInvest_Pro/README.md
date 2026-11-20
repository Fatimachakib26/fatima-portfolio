# QuantInvest Pro
**Smart Portfolio Optimization & Risk Analytics** — projet de Finance quantitative avancée (EMSI).

Application Streamlit d'optimisation de portefeuille selon le modèle de Markowitz :
données Yahoo Finance réelles, portefeuilles de variance minimale / Sharpe maximal,
frontière efficiente, mesures de risque (VaR, ES, drawdown) et backtest hors échantillon.

## Installation
```bash
cd QuantInvest_Pro
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Tests : `pytest -q tests`

## Architecture
| Dossier | Rôle |
|---|---|
| `config.py` | Paramètres par défaut et contraintes (séparés du code métier) |
| `core/` | Moteur quantitatif, sans dépendance à Streamlit, testé avec pytest |
| `components/` | Composants d'interface : sidebar, barre supérieure, KPI, thème Plotly |
| `pages/` | Les 6 pages de l'application |
| `assets/` | Feuille de style (design system) et logo |

## Avancement
- [x] Étape 1 : architecture, design system, navigation, page Paramètres
- [ ] Étape 2 : collecte et nettoyage des données (yfinance, cache, devises)
- [ ] Étape 3 : calculs financiers (rendements, μ, Σ)
- [ ] Étape 4 : optimisation Markowitz
- [ ] Étape 5 : frontière efficiente et graphiques
- [ ] Étape 6 : risque et backtesting
- [ ] Étapes 7 à 9 : intégration, tests, rapport
