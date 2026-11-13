# CRÉDIT HORIZON · RISK INTELLIGENCE — version Python / Streamlit / Power BI

Plateforme de gestion intelligente des risques financiers d'un organisme de financement des TPE.
Projet académique EMSI – *Contrôle interne & gestion des risques financiers* (cas fictif « Crédit Horizon »).

> Outil d'aide à l'analyse : l'application **ne prend jamais de décision d'octroi de crédit**.

## Lancer l'application

```bash
cd credit-horizon-streamlit
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py               # http://localhost:8501
```

Comptes de démonstration (mot de passe commun `Horizon2026!`) — boutons de pré-remplissage sur la page de connexion :
`admin@`, `directeur@`, `analyste@`, `commercial@`, `controleur@credithorizon.ma`.

## Tests

```bash
python -m unittest discover -s tests
```

10 tests : seuils et cotations R01–R08, analyse des dossiers, indicateurs, séparation des tâches, assistant, exports PDF/Excel/Power BI.

## Modules

| Page | Contenu |
|---|---|
| Dashboard exécutif | Indicateurs clés, répartition par catégorie et par niveau, évolution des scores, top 5, cartographie, indicateurs de contrôle interne, actions en attente |
| Power BI | Modèle en étoile (13 tables), classeur Excel, mesures DAX, guide, intégration du rapport publié |
| Registre des risques | R01–R08 du rapport ; ajout, modification, suppression, recherche, filtres ; score P × G et criticité automatiques ; historique |
| Cartographie | Matrice thermique 5 × 5 interactive (Faible vert, Modéré jaune, Élevé orange, Critique rouge) |
| Dossiers TPE | Formulaire complet, grille de vérification C01, complétude, incohérences, vigilance, synthèse ; analyse recalculée à chaque saisie ; inscription d'anomalie |
| Appétence au risque | Charte en trois niveaux, positionnement des risques, escalade, appétence par catégorie |
| Diagnostic COSO | 5 composantes, 17 principes, maturité, constats, lacunes, risques, recommandations, responsables, indicateurs |
| Fiches de contrôle | C01–C08 et matrice de couverture risques × contrôles |
| Suivi & anomalies | Plan d'action P1–P3, chaînes de recommandations, registre des anomalies avec escalade N1–N3 |
| Gouvernance RACI | 14 activités × 6 acteurs, contrôle automatique de la séparation des tâches, délégations, droits par rôle |
| Risk Advisor IA | Claude (API Anthropic) sur les données réelles ; 11 analyses prêtes à l'emploi ; export PDF ; moteur local de secours |
| Rapports & exports | PDF (rapport complet, synthèse exécutive, COSO, cartographie, plan d'action, rapport IA), Excel, CSV |
| Administration | Utilisateurs et rôles, journal d'audit, réinitialisation des données de démonstration |

## Intelligence artificielle

Créer `.streamlit/secrets.toml` (modèle : `.streamlit/secrets.toml.example`) :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
ANTHROPIC_MODEL = "claude-sonnet-5-5"
```

La clé reste côté serveur. Sans clé, l'assistant répond avec le moteur d'analyse local (mode signalé dans l'interface).

## Power BI

- Depuis l'application : page **Power BI** → « Jeu de données complet (ZIP) ».
- En ligne de commande : `python powerbi/export_powerbi.py` → `powerbi/data/` (un export initial y est déjà fourni).
- Pas à pas, relations du modèle et pages recommandées : `powerbi/GUIDE_POWER_BI.md` ; mesures : `powerbi/MESURES_DAX.dax`.
- Pour afficher le rapport publié dans l'application : `POWERBI_EMBED_URL = "https://app.powerbi.com/view?r=..."` dans les secrets.

## Déploiement gratuit (Streamlit Community Cloud)

1. share.streamlit.io → **New app** → dépôt `fatima-portfolio`, fichier principal `credit-horizon-streamlit/app.py`.
2. **Advanced settings → Secrets** : coller le contenu de `secrets.toml`.
3. Déployer. La base SQLite est recréée avec les données de démonstration à chaque redémarrage du serveur.

## Architecture

```
app.py                 connexion, navigation, rôles
core/scoring.py        méthode P × G et seuils du rapport
core/analysis.py       moteur d'analyse des dossiers TPE (aucune décision d'octroi)
core/db.py             SQLite, schéma, données du rapport (core/seed.json)
core/auth.py           mots de passe bcrypt, matrice des permissions (séparation des tâches)
core/advisor.py        Risk Advisor : Claude + moteur local
core/exports.py        PDF, Excel, CSV, modèle Power BI
core/charts.py         graphiques Plotly
views/*.py             une page par module
powerbi/               guide, mesures DAX, script et jeu de données
```

Données : les risques, contrôles, diagnostic COSO, RACI, charte, recommandations et plan d'action proviennent du rapport ;
les anomalies, dossiers TPE, historiques et avancements sont **fictifs** (marqués « Démo »). Les seuils des ratios d'analyse
des dossiers sont **indicatifs** (`core/analysis.py`, `THRESHOLDS`).
