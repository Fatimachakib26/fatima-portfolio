"""Exporte le modèle Power BI (CSV + classeur Excel) dans powerbi/data/ à partir de la base de l'application."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import db, exports, repo  # noqa: E402

if __name__ == "__main__":
    db.init()
    s = repo.snapshot()
    out = ROOT / "powerbi" / "data"
    out.mkdir(parents=True, exist_ok=True)
    for name, df in exports.powerbi_tables(s).items():
        df.to_csv(out / f"{name}.csv", index=False, sep=";", encoding="utf-8-sig")
    (out / "CreditHorizon_PowerBI.xlsx").write_bytes(exports.powerbi_excel(s))
    print(f"Jeu de données Power BI écrit dans {out}")
