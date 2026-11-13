# Rapport de qualité des données – SBA 7(a) FY2010–FY2019

Source : https://data.sba.gov/dataset/7a-504-foia · licence : U.S. Government Works (domaine public)

## Réconciliation

| Lignes brutes | Lignes propres | Lignes rejetées | Contrôle |
|---:|---:|---:|---|
| 545,751 | 544,605 | 1,146 | OK |

## Règles appliquées

| Règle | Description | Lignes avant | Lignes après | Remarque |
|---|---|---:|---:|---|
| R01 | Suppression des espaces en début/fin de texte | 545,751 | 545,751 | 677670 cellules corrigées |
| R02 | Suppression des doublons exacts (première occurrence conservée) | 545,751 | 544,615 |  |
| R03 | Normalisation des codes : « P I F » → PIF, Y/N → 1/0 ou booléen | 544,615 | 544,615 |  |
| R04 | Conversion des montants, taux et durées en nombres ; montant > 0 obligatoire | 544,615 | 544,615 |  |
| R05 | Conversion des dates ; date d'approbation obligatoire | 544,615 | 544,615 |  |
| R06 | Contrôle : garantie SBA ≤ montant approuvé | 544,615 | 544,615 |  |
| R07 | Contrôle : un prêt soldé/passé en perte a une date cohérente, postérieure à l'approbation | 544,615 | 544,605 |  |
| R08 | Suppression des données personnelles (nom, adresse, code postal de l'emprunteur) | 544,605 | 544,605 | BorrName, BorrStreet, BorrZip |
| R09 | Variables dérivées : secteur NAICS, tranches de montant et de durée, population d'analyse, défaut, délai et taux de perte | 544,605 | 544,605 |  |

## Rejets par règle

| Règle | Lignes |
|---|---:|
| R02 | 1,136 |
| R07 | 10 |

## Populations d'analyse

| Population | Prêts |
|---|---:|
| Dénoué | 431,972 |
| Non décaissé | 65,964 |
| En cours (non publié) | 46,669 |

Le taux de défaut est calculé uniquement sur les prêts **dénoués** (remboursés ou passés en perte) : les prêts non décaissés n'ont jamais porté de risque et l'issue des prêts « EXEMPT » n'est pas publiée.

## Profil du fichier brut (avant toute correction)

| Colonne | Vides | % vides | Valeurs distinctes | Exemples |
|---|---:|---:|---:|---|
| AsOfDate | 0 | 0.0 | 1 | 2026-09-30 |
| Program | 0 | 0.0 | 1 |  7A |
| LocationID | 1 | 0.0 | 3,112 | 0012096 / 0089255 / 0029760 |
| BorrName | 0 | 0.0 | 433,984 | United Renal Associates of Georgia, P.C. / Sylvia H. Caruso / Bangor Wine & Cheese |
| BorrStreet | 0 | 0.0 | 472,659 | 5669 Peachtree Dunwoody Road NE, Suite 2 / 5 BROADWAY, SUITE 104 / 436 State Street. |
| BorrCity | 0 | 0.0 | 26,418 | Atlanta / SAUGUS / Bangor |
| BorrState | 0 | 0.0 | 58 | GA / MA / ME |
| BorrZip | 0 | 0.0 | 24,035 | 30342 / 01906 / 04401 |
| BankName | 1 | 0.0 | 2,854 | Wells Fargo Bank National Association / TruNorth Bank / Machias Savings Bank |
| BankFDICNumber | 39,309 | 7.2 | 2,432 | 03511 / 26484 / 19531 |
| BankNCUANumber | 528,060 | 96.76 | 453 | 03943 / 05536 / 24692 |
| BankStreet | 1 | 0.0 | 3,013 | 3201 N 4th Ave / 248 Andover St, Route 114 / 4 Center St |
| BankCity | 1 | 0.0 | 2,137 | Sioux Falls / Peabody / MACHIAS |
| BankState | 1 | 0.0 | 56 | SD / MA / ME |
| BankZip | 1 | 0.0 | 2,608 | 57104 / 01960 / 04654 |
| GrossApproval | 0 | 0.0 | 20,014 | 51000.0 / 30000.0 / 74000.0 |
| SBAGuaranteedApproval | 0 | 0.0 | 26,978 | 25500.0 / 27000.0 / 66600.0 |
| ApprovalDate | 0 | 0.0 | 3,407 | 2009-10-01 / 2009-10-02 / 2009-10-05 |
| ApprovalFY | 0 | 0.0 | 10 | 2010 / 2011 / 2012 |
| FirstDisbursementDate | 67,051 | 12.29 | 3,678 | 2009-10-01 / 2010-02-01 / 2009-11-01 |
| ProcessingMethod | 0 | 0.0 | 24 | SBA Express Program / 7a General / Preferred Lenders Program |
| InitialInterestRate | 0 | 0.0 | 1,799 | 5.8 / 6.5 / 5.5 |
| FixedorVariableInterestInd | 0 | 0.0 | 2 | V / F |
| TermInMonths | 0 | 0.0 | 342 | 13.0 / 60.0 / 72.0 |
| NaicsCode | 2 | 0.0 | 1,269 | 621111 / 812113 / 424820 |
| NaicsDescription | 3 | 0.0 | 2,023 | Offices of Physicians (except Mental Hea / Nail Salons / Wine and Distilled Alcoholic Beverage Me |
| FranchiseCode | 498,201 | 91.29 | 5,074 | 03512 / 50965 / 70552 |
| FranchiseName | 498,307 | 91.31 | 4,446 | ALPHAGRAPHICS, PRINTSHOPS OF THE FUTU / MARCO'S PIZZA / RODEWAY INNS |
| ProjectCounty | 0 | 0.0 | 1,899 | FULTON / ESSEX / PENOBSCOT |
| ProjectState | 0 | 0.0 | 58 | GA / MA / ME |
| SBADistrictOffice | 0 | 0.0 | 67 | GEORGIA DISTRICT OFFICE / MASSACHUSETTS DISTRICT OFFICE / MAINE DISTRICT OFFICE |
| CongressionalDistrict | 29 | 0.01 | 55 | 05 / 06 / 02 |
| BusinessType | 32 | 0.01 | 4 | CORPORATION / INDIVIDUAL / PARTNERSHIP |
| BusinessAge | 1,861 | 0.34 | 11 | New, Less than 1 Year old / Existing, 5 or more years / Less than 4 years old but at least 3 |
| LoanStatus | 0 | 0.0 | 5 | P I F / EXEMPT / CHGOFF |
| PaidInFullDate | 148,030 | 27.12 | 203 | 2010-11-30 / 2013-11-30 / 2015-11-30 |
| ChargeOffDate | 511,207 | 93.67 | 3,656 | 2015-03-19 / 2012-03-22 / 2015-07-14 |
| GrossChargeOffAmount | 0 | 0.0 | 33,386 | 0.0 / 226624.93 / 11989.8 |
| RevolverStatus | 0 | 0.0 | 2 | Y / N |
| JobsSupported | 2 | 0.0 | 313 | 6.0 / 1.0 / 3.0 |
| CollateralInd | 0 | 0.0 | 2 | N / Y |
| SoldSecMrktInd | 417,762 | 76.55 | 3 | Y / N |
