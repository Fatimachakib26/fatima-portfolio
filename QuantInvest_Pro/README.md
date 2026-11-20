# QuantInvest Pro
**Smart Portfolio Optimization & Risk Analytics** — projet de Finance quantitative avancée, EMSI.

Application web interactive (Streamlit) d'optimisation de portefeuille selon le modèle de
Harry Markowitz (1952), alimentée par des données réelles Yahoo Finance, avec une validation
hors échantillon rigoureuse.

---

## Sujet et problématique
**Sujet :** « Optimisation de portefeuille avec Markowitz » — estimer les rendements moyens et la
covariance d'actifs disposant d'un historique commun, trouver les portefeuilles de **variance
minimale** et de **Sharpe maximal** sous contraintes, les comparer au portefeuille **équipondéré
(1/N)** et vérifier la performance sur une période différente de celle de l'estimation.

**Problématique :**
> Les portefeuilles optimisés par Markowitz font-ils vraiment mieux qu'un portefeuille
> équipondéré, une fois testés sur une période différente de celle de l'estimation ?
> Et quelles méthodes rendent l'optimisation plus robuste ?

---

## Installation et lancement
Prérequis : **Python 3.10 ou plus récent** (3.12 recommandé) et une connexion Internet.

```bash
cd QuantInvest_Pro
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
L'application s'ouvre sur http://localhost:8501.

Tests automatiques (sans Internet, données synthétiques à graine fixe) :
```bash
python -m pytest -q tests
```

> Si Chrome traduit la page (« Fin » devient « Ailette »), désactivez la traduction automatique.
> L'application se déclare en français et demande à ne pas être traduite.

---

## Pages de l'application
| Page | Contenu |
|---|---|
| **Tableau de bord** | Carte **Verdict** générée à partir des résultats hors échantillon (test de Memmel), KPI du portefeuille retenu sur la période de test, filtres (actifs, dates), performance base 100 contre le S&P 500, cartes d'actifs, frontière, allocation, corrélations, comparaison des 3 portefeuilles |
| **Optimisation** | *Données et estimation* (μ, σ, Σ, heatmap des corrélations) · *Portefeuilles optimaux* (avec et sans plafond, exports CSV / Excel) · *Frontière efficiente* (frontière exacte, nuage Monte-Carlo, droite de marché des capitaux) · *Contribution au risque* · *Ledoit-Wolf* |
| **Risque** | Sharpe, Sortino, Calmar, drawdown maximal, VaR historique et paramétrique, CVaR (estimation et test) · distribution des rendements contre loi normale (Jarque-Bera) · corrélation moyenne glissante avec périodes de crise |
| **Test rétrospectif** | Estimation contre test · frontière estimée vs réalisée · **fenêtre glissante** (4 stratégies, frais, rotation, nombre effectif de titres, Sharpe annoncé vs réalisé) · **significativité** (Memmel, bootstrap) · **carte de sensibilité** · export CSV pour Power BI |
| **Actifs** | Prix ajustés, statistiques descriptives, **CAPM** (bêta, alpha, R²), comparaison base 100, origine et qualité des données |
| **Paramètres** | Actifs, période, **date de séparation**, fréquence, taux sans risque, bornes et plafond, estimateur de covariance, fenêtre, rééquilibrage, frais · méthodologie · **contrôle de l'optimiseur** · correspondance avec les scripts du cours |

Chaque graphique est accompagné d'un encadré **« Comment lire »** et d'un encadré **« À retenir »**
dont les chiffres sont calculés à partir des résultats.

---

## Méthodologie (résumé)
**Données.** Cours de clôture ajustés (dividendes et splits) via `yfinance`. Report de la dernière
valeur limité à 3 séances (jamais vers l'arrière), exclusion des actifs avec plus de 10 % de valeurs
manquantes, conservation des seules dates communes. En cas d'échec du téléchargement : nouvelle
tentative, puis dernières données valides conservées en cache (horodatées).
Benchmark : ETF **SPY** (rendement total), cohérent avec les cours ajustés des actions.

**Estimation.** Rendements simples r = P_t / P_{t−1} − 1 ; μ = 252 × moyenne ; Σ = 252 × covariance
(empirique ou **Ledoit-Wolf**). Taux sans risque périodique (1 + rf)^(1/252) − 1.

**Optimisation (SciPy SLSQP).** Σwᵢ = 1, 0 ≤ wᵢ ≤ plafond (40 % par défaut, pas de vente à
découvert). Variance minimale : min wᵀΣw. Sharpe maximal : max (wᵀμ − r_f) / √(wᵀΣw), avec
plusieurs points de départ déterministes. Frontière exacte : variance minimale pour 30 à 40
rendements cibles. Convergence et contraintes vérifiées après chaque résolution.
**Contrôle :** sans bornes, le résultat numérique est comparé à la formule fermée
w* = Σ⁻¹1 / (1ᵀΣ⁻¹1) (écart < 10⁻⁴).

**Indicateurs.** Rendement annualisé (TCAM), volatilité, Sharpe, Sortino (écart-type de baisse de
Sortino et Price), Calmar, drawdown maximal, VaR 95 % historique et paramétrique, CVaR 95 %,
contribution au risque RCᵢ = wᵢ(Σw)ᵢ/σₚ (somme = σₚ), nombre effectif de titres 1/Σwᵢ².

**Validation sans biais d'anticipation.**
- *Séparation simple :* poids estimés jusqu'à la date de séparation (31/12/2023 par défaut), puis figés.
- *Fenêtre glissante :* à la clôture de la séance t, estimation sur [t − W + 1, t] uniquement ; les
  poids s'appliquent au rendement de t + 1, puis dérivent avec les cours ; rééquilibrage toutes les
  21 séances ; frais = points de base × Σ|Δw| (achat initial inclus). Toutes les stratégies
  démarrent à la même date. Ces garanties sont marquées `[no look-ahead]` dans `core/backtest.py`
  et testées (`test_no_look_ahead_future_changes_do_not_affect_past_weights`).
- *Significativité :* test de Memmel (2003) sur la différence de Sharpe avec le 1/N ; intervalle de
  confiance à 95 % du Sharpe par bootstrap (1 000 tirages, graine 42).

---

## Exemple de résultats (données du 20/11/2026)
6 actions (AAPL, MSFT, NVDA, AMZN, GOOGL, META), estimation 01/2019 – 12/2023, test 01/2024 –
11/2026, plafond 40 %, taux sans risque 4 % :

| Portefeuille | Sharpe estimé | Sharpe en test |
|---|---|---|
| Variance minimale | 0,91 | 0,83 |
| Sharpe maximal | **1,24** | 0,99 |
| Équipondéré (1/N) | 0,99 | 0,94 |

Le Sharpe maximal reste devant le 1/N hors échantillon, mais l'écart **n'est pas significatif**
(test de Memmel, p ≈ 0,87), et l'optimiseur surestime sa propre performance (1,24 annoncé contre
0,99 obtenu). En fenêtre glissante, aucune stratégie ne se distingue significativement du 1/N.
Ces conclusions rejoignent DeMiguel, Garlappi et Uppal (2009). *Les chiffres évoluent à chaque
actualisation des données.*

---

## Architecture
```
QuantInvest_Pro/
├── app.py                 Point d'entrée : thème, navigation, chargement des données
├── config.py              Paramètres par défaut et contraintes (séparés du code métier)
├── core/                  Moteur de calcul, sans Streamlit, testé avec pytest
│   ├── data_loader.py     Téléchargement, nouvelle tentative, cache, devises
│   ├── preprocessing.py   Nettoyage, historique commun, fréquence
│   ├── returns.py         Rendements, μ, Σ, corrélation glissante
│   ├── robust.py          Covariance empirique / Ledoit-Wolf
│   ├── optimization.py    Markowitz (SLSQP), frontière, contrôle analytique
│   ├── portfolio.py       Performance, risque, contributions au risque
│   ├── backtest.py        Séparation simple, frontière réalisée, fenêtre glissante, sensibilité
│   ├── stats_tests.py     Test de Memmel, bootstrap
│   ├── capm.py            Bêta, alpha, statistiques descriptives
│   ├── verdict.py         Synthèse en une phrase
│   └── reporting.py       Exports CSV (format long) et Excel
├── components/            Interface : thème, menu, KPI, graphiques, formats français, cache
├── pages/                 Les 6 pages (affichage uniquement)
├── assets/                Feuille de style, logo
└── tests/                 51 tests unitaires
```

---

## Limites
- **Rendements passés ≠ rendements futurs** : μ est l'entrée la plus bruitée du modèle ; c'est la
  principale cause de l'écart entre Sharpe annoncé et réalisé.
- **Hypothèse de normalité** : les rendements observés ont des queues épaisses (kurtosis élevée) ;
  la VaR paramétrique sous-estime alors le risque.
- **Univers réduit et biais du survivant** : 6 grandes valeurs technologiques américaines qui ont
  connu une forte hausse ; les conclusions ne se généralisent pas à tout le marché.
- **Taux sans risque constant**, exécution au cours de clôture, actions fractionnables, pas
  d'impôts ni de contrainte de liquidité.
- **Puissance statistique limitée** : quelques années de données ne permettent pas de distinguer
  des écarts de Sharpe de 0,2 à 0,3.
- Devises multiples non converties (alerte affichée).

---

## Références
- Markowitz, H. (1952). *Portfolio Selection*. Journal of Finance.
- Ledoit, O., Wolf, M. (2004). *Honey, I Shrunk the Sample Covariance Matrix*.
- Memmel, C. (2003). *Performance Hypothesis Testing with the Sharpe Ratio*.
- DeMiguel, V., Garlappi, L., Uppal, R. (2009). *Optimal Versus Naive Diversification*.
- Sortino, F., Price, L. (1994). *Performance Measurement in a Downside Risk Framework*.
