# CRÉDIT HORIZON · RISK INTELLIGENCE — site autonome

`../credit_horizon_site.html` est la plateforme complète en **un seul fichier HTML** (aucun serveur, aucune dépendance externe) :
il suffit de l'ouvrir dans un navigateur. Les modifications sont conservées dans le navigateur (stockage local).

Modules : dashboard, registre des risques (ajout / modification / suppression / recherche), cartographie 5 × 5,
analyse des dossiers TPE en temps réel, diagnostic COSO, fiches de contrôle, suivi des actions et anomalies,
gouvernance RACI, appétence au risque, Risk Advisor (moteur d'analyse intégré), exports CSV/JSON, journal d'audit.

Reconstruire le fichier après une modification des sources :

```bash
cd credit-horizon-site
npm install
node build.mjs          # écrit ../credit_horizon_site.html
```

Les moteurs (`src/logic/`) sont les mêmes que ceux de la version Next.js ; les données (`src/seed.json`) sont celles du rapport EMSI.
Le rapport PDF complet est fourni à part : `../Credit_Horizon_Rapport_Risques.pdf`.
