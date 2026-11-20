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
| Groupe | Page | Contenu |
|---|---|---|
| Analyse | **Tableau de bord** | Verdict hors échantillon (Memmel), tableau des 3 portefeuilles et du SPY, valeur de 100 investis, KPI traçables, frontière, pondérations, corrélations |
| Analyse | **Portefeuilles** | Fiche de chaque portefeuille : composition, *pourquoi ces poids ?* (entrées, contraintes actives, sensibilité des poids à μ), performance (heatmap mensuelle, sélection d'une zone de dates), attribution, risque, promesse contre réalité ; **bibliothèque** (constructeur, portefeuille cible, duplication, import/export JSON) |
| Analyse | **Comparateur** | 24 indicateurs côte à côte (meilleur en vert, pire en rouge, détail traçable), radar, courbes, poids, contributions au risque, corrélations, p-valeurs de Memmel, **rapport HTML** |
| Analyse | **Indicateurs** | Définition, formule, calcul pas à pas, comparaison portefeuilles / actifs, évolution glissante, lecture et limites |
| Méthode | **Optimisation** | Données et estimation, portefeuilles optimaux et effet du plafond, **frontière cliquable** et volatilité cible, frontière estimée contre réalisée, contribution au risque, Ledoit-Wolf, diversification (TLT, GLD), **panneau de contraintes** (bornes par actif, plafonds par secteur) |
| Méthode | **Risque** | Indicateurs (Sortino, Calmar, VaR, CVaR), distribution, corrélation glissante, **scénarios** (crises, choc hypothétique, Monte-Carlo) |
| Méthode | **Test rétrospectif** | Estimation contre test, fenêtre glissante, significativité, sensibilité (durée d'estimation et fenêtre glissante), export Power BI |
| Données | **Actifs** | Fiche action : profil, prix et performance, risque, fondamentaux, rôle dans les portefeuilles, comparaison, qualité des données |
| Données | **Sources et méthodologie** | Origine de chaque série, traitements, toutes les formules, contrôle de l'optimiseur, hypothèses, références, scripts du cours, journal des calculs |
| Données | **Paramètres** | Actifs, période, date de séparation, fréquence, taux sans risque, bornes, estimateur, fenêtre, rééquilibrage, frais |

**Traçabilité** : chaque indicateur est un objet `Resultat` (valeur, formule, entrées, calcul détaillé avec les vrais
nombres, source avec date de téléchargement, période). Le bouton « ⓘ D'où vient ce chiffre ? » l'affiche, avec les
données utilisées exportables en CSV. Un test vérifie que le calcul détaillé redonne la valeur.

**Barre de sélection globale** : portefeuilles, actifs, période (estimation, test, toute la période, krach Covid,
hausse des taux 2022, personnalisée), indice, fréquence — conservée d'une page à l'autre. Les poids ne sont jamais
réestimés sur la période affichée.

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
├── views/                 Les pages (affichage uniquement)
├── assets/                Feuille de style, logo
└── tests/                 101 tests unitaires
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
