"""Exécute tout le pipeline : acquisition → intégrité → profilage/nettoyage → tables d'analyse.

Usage :
    python run.py            # télécharge si nécessaire, puis traite
    python run.py --force    # retélécharge la source officielle
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import clean, ingest, marts  # noqa: E402

if __name__ == "__main__":
    t = time.time()
    print("1/4 Acquisition de la source officielle")
    m = ingest.run(force="--force" in sys.argv)
    f = m["files"]["loans"]
    print(f"    {f['name']} : {f['rows']:,} lignes × {f['columns']} colonnes, {f['bytes'] / 1e6:.1f} Mo, sha256 {f['sha256'][:16]}…")
    print("2/4 Contrôle d'intégrité")
    ingest.verify()
    print("3/4 Profilage, validation et nettoyage")
    out = clean.run()
    s = out["summary"]
    print(f"    {s['raw_rows']:,} brutes = {s['clean_rows']:,} propres + {s['rejected_rows']:,} rejetées · rejets {s['rejects_by_rule']}")
    print("4/4 Tables d'analyse (marts)")
    p = marts.run(out["df"])
    o = p["overview"]
    print(f"    {o['loans_resolved']:,} prêts dénoués · taux de défaut {o['default_rate']:.2%} · taux de perte {o['loss_rate']:.2%}")
    print(f"Terminé en {time.time() - t:.0f} s. Rapports : reports/ · tables : data/marts/")
