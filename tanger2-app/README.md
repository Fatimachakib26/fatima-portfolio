# Tanger II — Simulateur interactif de montage financier

Application **Python / Streamlit** de démonstration du projet « Financement de l'unité industrielle Tanger II »
(Détroit Plasturgie Automobile — société et projet **fictifs**, cas pédagogique), avec export vers **Power BI**.

## Lancer l'application

```bash
cd tanger2-app
pip install -r requirements.txt
streamlit run app.py
```

Ouvrir http://localhost:8501.

| Identifiant | Mot de passe  | Rôle    | Accès |
|-------------|---------------|---------|-------|
| `admin`     | `Tanger2026!` | admin   | toutes les pages (dont optimiseur et export Power BI) |
| `jury`      | `Jury2026`    | lecteur | tableau de bord, simulateur, formulaire, sensibilités, Monte-Carlo, simulation en direct |

Mots de passe hachés (PBKDF2-SHA256, 200 000 itérations, sel), verrouillage 60 s après 5 échecs.
Pour d'autres comptes : copier `.streamlit/secrets.example.toml` en `.streamlit/secrets.toml` (non versionné).

## Pages

1. **Tableau de bord** : indicateurs clés, comparaison A / B / C, activité, DSCR, trésorerie, diagramme ressources → emplois.
2. **Simulateur (curseurs)** : chocs (prix, volumes, matières, énergie, délai clients, CAPEX, retard, taux, prime) et
   mesures correctrices (apport, dette de réserve, différé, allongement, investissements reportés), recalcul instantané.
3. **Formulaire** : saisir une structure de financement personnalisée → contrôles des contraintes + radar multicritère.
4. **Sensibilités & stress** : diagramme tornade, carte de chaleur 2D, table des 8 cas (central, prudent, favorable, stress…).
5. **Monte-Carlo** : 7 facteurs de risque corrélés (copule gaussienne, Cholesky), VaR 5 % de la VAN, probabilité de bris de covenant.
6. **Optimiseur** : recherche sur grille de la structure FP / dette / crédit-bail qui maximise le TRI des fonds propres
   sous contraintes (capacité d'apport, plafond bancaire, DSCR ≥ 1,20x, levier ≤ 3,5x, trésorerie ≥ 0), frontière rendement / risque.
7. **Simulation en direct** : film animé 2027 → 2038 avec jauge DSCR, Monte-Carlo en temps réel (convergence),
   « épreuve finale » : choc tiré au sort + recherche automatique des mesures correctrices.
8. **Export Power BI** : schéma en étoile (faits annuels, faits KPI, dimensions) en CSV ou Excel + mesures DAX.

## Le modèle (`model.py`)

Réplique Python des hypothèses de l'onglet 02 du modèle Excel : montée en cadence avec retard
(`u(k) = (1 − f)·R(k − q) + f·R(k − q − 1)`), CAPEX par poste et semestre, amortissements par catégorie,
BFR en rythme de sortie, IS marocain (20 % / 35 % au-delà de 100 MDH, cotisation minimale, exonération de 5 ans,
report des déficits), dette semestrielle (différé, annuités constantes), crédit-bail, prime + crédit relais,
cascade de trésorerie avec blocage des dividendes, DSCR, dette nette retraitée / EBITDA,
WACC (CAPM, bêta réendetté de Hamada), VAN / TRI projet, TRI des fonds propres, point mort.

Calibrage par rapport à l'Excel (cas central, onglet 21_Comparaison) :

| Indicateur | Excel A / B / C | Python A / B / C |
|---|---|---|
| VAN projet (MDH) | 107,5 / 114,2 / 272,5 | 107,6 / 113,7 / 278,1 |
| TRI projet | 12,98 % / 12,98 % / 16,86 % | 12,98 % / 12,98 % / 17,07 % |
| TRI des fonds propres | 15,41 % / 17,20 % / 22,41 % | 15,16 % / 16,94 % / 22,41 % |
| WACC | 10,51 % / 10,37 % / 10,35 % | 10,51 % / 10,38 % / 10,36 % |
| DSCR minimum | 1,58x / 1,37x / 1,64x | 1,59x / 1,38x / 1,63x |
| Dette nette retraitée / EBITDA max | 1,33x / 1,73x / 1,47x | 1,36x / 1,75x / 1,39x |

Mécanismes repris de l'Excel : tirages des fonds propres, de la dette et du relais au prorata des emplois
(le crédit-bailleur règle sa part des machines au rythme de leurs décaissements), intérêts intercalaires et frais
immobilisés en non-valeurs amortis à 20 %, dividendes versés en N sur le résultat de N−1 après réserve légale
et dans la limite de la trésorerie au-delà de 40 MDH. En stress, les besoins non financés diffèrent de
quelques dizaines de MDH (stress combiné B : 126 contre 137 MDH ; VAN −89 contre −82 MDH).
**L'Excel reste la référence** pour les chiffres du rapport.

Tests de non-régression (calage sur l'Excel, stress, Monte-Carlo) : `pip install pytest` puis `python -m pytest tests`.

## Power BI

- **Fichiers** : page « Export Power BI » → pack CSV (`;` et virgule décimale) ou classeur Excel → Power BI Desktop → *Obtenir les données*.
- **Script Python** : Power BI → *Obtenir les données → Script Python* → coller `powerbi/export_powerbi.py`
  (adapter `APP_DIR`). Ou en ligne de commande : `python powerbi/export_powerbi.py` écrit les CSV dans `export/`.
- Relations : `fait_annuel[Scénario] → dim_scenario[Scénario]`, `fait_annuel[Cas] → dim_cas[Cas]` (idem `fait_kpi`).

## Déploiement gratuit

Streamlit Community Cloud : pousser le dépôt sur GitHub → share.streamlit.io → *New app* →
fichier principal `tanger2-app/app.py`. Définir les comptes dans *Settings → Secrets* (même format que `secrets.example.toml`).
