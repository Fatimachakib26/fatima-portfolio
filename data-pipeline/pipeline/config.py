"""Paramètres du pipeline : une seule source de vérité pour les chemins et la source officielle."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
MARTS = ROOT / "data" / "marts"
REPORTS = ROOT / "reports"

SOURCE = {
    "publisher": "U.S. Small Business Administration (SBA) – Office of the Chief Data Officer",
    "dataset": "7(a) & 504 FOIA",
    "dataset_identifier": "SBA-OHA-2016-08-001",
    "landing_page": "https://data.sba.gov/dataset/7a-504-foia",
    "license": "U.S. Government Works (domaine public)",
    "update_frequency": "Trimestrielle (environ un mois après la fin du trimestre)",
    "files": {
        "loans": {
            "name": "FOIA_7a_FY2010_FY2019_asof_260930.csv",
            "url": "https://data.sba.gov/sites/default/files/uploaded_resources/FOIA_7a_FY2010_FY2019_asof_260930.csv",
            "description": "Prêts garantis 7(a) approuvés entre les exercices fiscaux 2010 et 2019, situation au 30/09/2026",
        },
        "dictionary": {
            "name": "7a_504_foia_data_dictionary.xlsx",
            "url": "https://data.sba.gov/sites/default/files/uploaded_resources/7a_504_foia_data_dictionary.xlsx",
            "description": "Dictionnaire officiel des champs",
        },
    },
}

# Colonnes à caractère personnel : supprimées dès la couche « clean » (minimisation des données).
PII_COLUMNS = ["BorrName", "BorrStreet", "BorrZip"]

# Secteurs NAICS (2 premiers chiffres) – libellés officiels NAICS, traduits en français.
NAICS_SECTORS = {
    "11": "Agriculture, sylviculture, pêche et chasse",
    "21": "Mines, carrières, pétrole et gaz",
    "22": "Services publics (énergie, eau)",
    "23": "Construction",
    "31": "Industrie manufacturière", "32": "Industrie manufacturière", "33": "Industrie manufacturière",
    "42": "Commerce de gros",
    "44": "Commerce de détail", "45": "Commerce de détail",
    "48": "Transport et entreposage", "49": "Transport et entreposage",
    "51": "Information et communication",
    "52": "Finance et assurance",
    "53": "Immobilier et location",
    "54": "Services professionnels, scientifiques et techniques",
    "55": "Gestion de sociétés",
    "56": "Services administratifs et de soutien",
    "61": "Enseignement",
    "62": "Santé et action sociale",
    "71": "Arts, spectacles et loisirs",
    "72": "Hébergement et restauration",
    "81": "Autres services",
    "92": "Administration publique",
}

SIZE_BANDS = [(0, 50_000, "≤ 50 k$"), (50_000, 150_000, "50–150 k$"), (150_000, 350_000, "150–350 k$"),
              (350_000, 1_000_000, "350 k$–1 M$"), (1_000_000, float("inf"), "> 1 M$")]
TERM_BANDS = [(0, 12, "≤ 1 an"), (12, 60, "1–5 ans"), (60, 120, "5–10 ans"), (120, float("inf"), "> 10 ans")]
