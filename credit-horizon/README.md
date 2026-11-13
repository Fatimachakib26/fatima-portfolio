# CRÉDIT HORIZON · RISK INTELLIGENCE

Application web de gestion intelligente des risques financiers pour un organisme de financement des TPE.
Projet académique EMSI – *Contrôle interne & gestion des risques financiers* (cas fictif « Crédit Horizon »).

> Outil d'aide à l'analyse et à la décision : la plateforme **ne prend jamais de décision d'octroi de crédit**.

## Modules

| # | Module | Contenu |
|---|--------|---------|
| 1 | Dashboard exécutif | KPI, répartition par catégorie et par niveau, évolution des scores, top 5, indicateurs de contrôle interne, actions en attente |
| 2 | Registre des risques | R01–R08 du rapport, ajout / modification / suppression / recherche / filtres, score P × G et criticité calculés automatiquement, historique des cotations |
| 3 | Cartographie | Matrice thermique 5 × 5 interactive (Faible vert, Modéré jaune, Élevé orange, Critique rouge) |
| 4 | Dossiers TPE | Formulaire complet, grille de vérification C01, complétude, informations manquantes, incohérences, points de vigilance, synthèse ; déclaration d'anomalie en un clic |
| 5 | Diagnostic COSO 2013 | 5 composantes, 17 principes : constats, lacunes, risques, recommandations, responsables, indicateurs, maturité |
| 6 | Contrôle interne | Fiches C01–C08 (objectif, risque, type, procédure, responsable, fréquence, preuve, indicateur, anomalies) + matrice de couverture |
| 7 | Gouvernance RACI | 14 activités × 6 acteurs, contrôle automatique de la séparation des tâches, délégations, droits par rôle |
| 8 | Appétence au risque | Charte en 3 niveaux, positionnement des risques, escalade, appétence par catégorie |
| 9 | **Risk Advisor (IA)** | Assistant génératif connecté aux données réelles ; 12 analyses prêtes à l'emploi ; recommandations au format RISQUE → LACUNE COSO → ACTION → RESPONSABLE → INDICATEUR |
| 10 | Rapports & exports | PDF (rapport complet, synthèse exécutive, COSO, cartographie, plan d'action, rapport IA), Excel multi-onglets, CSV |
| – | Suivi | Plan d'action P1–P3, chaînes de recommandations, registre des anomalies avec escalade N1–N3 |
| – | Administration | Utilisateurs et rôles, état technique, journal d'audit, réinitialisation de la démo |

## Architecture

- **Frontend** : Next.js 15 (App Router), React 19, Tailwind CSS, Recharts, lucide-react
- **Backend** : routes API Next.js sécurisées (validation Zod, contrôle des permissions par rôle côté serveur, journal d'audit)
- **Base de données** : PostgreSQL – Supabase via `DATABASE_URL` ; sans variable, PostgreSQL embarqué (PGlite) persistant dans `./.data`
- **Authentification** : comptes en base (mots de passe bcrypt), session JWT en cookie `httpOnly`, 5 rôles (Administrateur, Directeur, Analyste risques, Commercial, Contrôleur interne)
- **IA** : Vercel AI SDK → **Vercel AI Gateway** (`AI_GATEWAY_API_KEY`, ou OIDC automatique sur Vercel), ou clé Anthropic directe. Les clés ne quittent jamais le serveur. Sans clé, un moteur d'analyse local répond à partir des mêmes données (mode signalé dans l'interface).

## Démarrage local

```bash
cd credit-horizon
npm install
cp .env.example .env.local   # facultatif : clés IA, Supabase, AUTH_SECRET
npm run dev                  # http://localhost:3000
```

Comptes de démonstration (mot de passe commun `Horizon2026!`) :
`admin@`, `directeur@`, `analyste@`, `commercial@`, `controleur@credithorizon.ma`.

Tests : `npm test` (scoring et moteur d'analyse des dossiers) · `npm run typecheck` · `npm run build`.

## Déploiement Vercel + Supabase

1. **Supabase** : créer un projet, copier la chaîne de connexion *Transaction pooler* (port 6543). Le schéma est créé automatiquement au premier démarrage (il est aussi fourni dans `supabase/schema.sql`) et les données de démonstration sont insérées si la base est vide.
2. **Vercel** : importer le dépôt, définir **Root Directory = `credit-horizon`**.
3. Variables d'environnement Vercel :
   - `DATABASE_URL` – chaîne Supabase
   - `AUTH_SECRET` – `openssl rand -base64 32`
   - `AI_GATEWAY_API_KEY` – clé Vercel AI Gateway (facultative sur Vercel grâce à l'OIDC) ; `AI_MODEL` (défaut `anthropic/claude-sonnet-4.5`)
4. Déployer. Vérifier l'état dans **Administration** (base, IA, secret).

Sans `DATABASE_URL` sur Vercel, l'application fonctionne mais la base embarquée est éphémère (réinitialisée à chaque redémarrage d'instance) : à réserver à une démonstration.

## Données

Les risques R01–R08, contrôles C01–C08, diagnostic COSO, RACI, charte d'appétence, recommandations et plan d'action sont repris du rapport académique. Les anomalies, dossiers TPE, historiques de cotation et avancements sont **fictifs** et marqués « Démo ». Les seuils des ratios d'analyse des dossiers sont **indicatifs** et paramétrables (`src/lib/dossier-analysis.ts`).
