"""Source de données Python pour Power BI (Obtenir les données → Script Python).

Power BI exécute ce script et propose chaque DataFrame (fait_annuel, fait_kpi, dim_scenario, dim_cas)
comme table. Adapter APP_DIR au chemin local du dossier tanger2-app.
Peut aussi être lancé en ligne de commande : python export_powerbi.py  → écrit des CSV dans ./export
"""
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd

APP_DIR = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path(r"C:\chemin\vers\tanger2-app")
sys.path.insert(0, str(APP_DIR))
import model as M  # noqa: E402

rows, kpis = [], []
for cas, sh in M.CASES.items():
    for sc, fin in M.SCENARIOS.items():
        r = M.run(fin, sh)
        t = pd.DataFrame(r["table"]).melt(id_vars="Année", var_name="Indicateur", value_name="Valeur")
        t.insert(0, "Cas", cas)
        t.insert(0, "Scénario", sc)
        rows.append(t)
        kpis += [{"Scénario": sc, "Cas": cas, "Indicateur": k, "Valeur": float(v)} for k, v in r["kpi"].items()]

fait_annuel = pd.concat(rows, ignore_index=True)
fait_kpi = pd.DataFrame(kpis)
dim_scenario = pd.DataFrame([{"Scénario": k, **asdict(f)} for k, f in M.SCENARIOS.items()])
dim_cas = pd.DataFrame([{"Cas": c, **asdict(s)} for c, s in M.CASES.items()])

if __name__ == "__main__":
    out = Path("export")
    out.mkdir(exist_ok=True)
    for name in ("fait_annuel", "fait_kpi", "dim_scenario", "dim_cas"):
        globals()[name].to_csv(out / f"{name}.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
    print(f"CSV écrits dans {out.resolve()}")
