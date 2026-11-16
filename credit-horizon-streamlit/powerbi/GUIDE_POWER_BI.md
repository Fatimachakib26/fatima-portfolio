# Power BI – CRÉDIT HORIZON RISK INTELLIGENCE

Le jeu de données est produit par l'application Streamlit (page **Power BI**, bouton « Télécharger le jeu de données Power BI »)
ou en ligne de commande : `python powerbi/export_powerbi.py` (fichiers écrits dans `powerbi/data/`).

## 1. Importer les données
1. Power BI Desktop → **Obtenir les données → Classeur Excel** → `CreditHorizon_PowerBI.xlsx`
   (ou **Texte/CSV** pour chaque fichier, séparateur `;`, encodage UTF-8).
2. Cocher toutes les tables → **Charger**.
3. Pour une actualisation automatique, placer le dossier sur OneDrive/SharePoint et relancer l'export depuis l'application.

## 2. Modèle en étoile (vue Modèle → relations)
| De (plusieurs) | Vers (un) | Clé |
|---|---|---|
| PontRisqueControle | DimRisque | RisqueID |
| PontRisqueControle | DimControle | ControleID |
| PontRisquePrincipe | DimRisque | RisqueID |
| PontRisquePrincipe | DimPrincipeCOSO | PrincipeID |
| DimPrincipeCOSO | DimComposanteCOSO | ComposanteID |
| FaitCotation | DimRisque | RisqueID |
| FaitAnomalie | DimRisque | RisqueID |
| FaitAnomalie | DimControle | ControleID |
| PontActionRisque | DimRisque | RisqueID |
| PontActionRisque | FaitAction | ActionID |
| FaitRecommandation | DimRisque | RisqueID |

Pour les tables « Pont », régler la direction de filtrage croisé sur **Les deux**.
Trier `DimRisque[Niveau]` par `DimRisque[OrdreNiveau]` (Outils de colonne → Trier par colonne).

## 3. Mesures
Créer une table de mesures et coller les mesures du fichier `MESURES_DAX.dax`.

## 4. Pages de rapport recommandées
1. **Dashboard exécutif** : cartes (Nb Risques, Nb Risques Critiques, Taux Couverture, Avancement Moyen, Anomalies Ouvertes, Maturité Moyenne COSO) ;
   anneau par `Categorie` ; histogramme par `Niveau` (couleur = mesure *Couleur Niveau*) ; courbe `FaitCotation[Date]` × *Score Moyen Historique*.
2. **Cartographie 5 × 5** : visuel *Matrice* avec `Probabilite` en lignes (tri décroissant), `Gravite` en colonnes, valeur = `RisqueID` (Première),
   mise en forme conditionnelle de l'arrière-plan par *Score Max* (dégradé vert → jaune → orange → rouge, seuils 4 / 9 / 15 / 25).
3. **Contrôle interne** : matrice `DimRisque[RisqueID]` × `DimControle[ControleID]` (valeur : nombre de lignes du pont) + *Risque en Dependance*.
4. **COSO 2013** : radar ou barres `Composante` × `Maturite` ; tableau des 17 principes avec mise en forme sur `Appreciation`.
5. **Suivi** : tableau du plan d'action (barre de données sur `Avancement`), anomalies par statut et niveau d'escalade.

## 5. Intégrer le rapport dans Streamlit
Publier le rapport (Power BI Service → Fichier → **Incorporer le rapport → Publier sur le web** ou lien d'incorporation sécurisé),
puis renseigner l'URL dans `.streamlit/secrets.toml` :

```toml
POWERBI_EMBED_URL = "https://app.powerbi.com/view?r=..."
```

La page **Power BI** de l'application affiche alors le rapport. « Publier sur le web » rend le rapport public :
pour des données réelles, utiliser l'incorporation sécurisée (Power BI Embedded / lien organisationnel).
