"""Tests automatisés : python -m unittest discover -s tests"""
import io
import os
import sys
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["CH_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from core import auth, db, exports, repo  # noqa: E402
from core.advisor import offline_answer  # noqa: E402
from core.analysis import analyze_dossier  # noqa: E402
from core.scoring import level, score  # noqa: E402

db.init()


class Scoring(unittest.TestCase):
    def test_seuils_du_rapport(self):
        self.assertEqual([level(s) for s in (4, 5, 9, 10, 15, 16, 25)], ["Faible", "Modéré", "Modéré", "Élevé", "Élevé", "Critique", "Critique"])
        self.assertEqual(score(9, 0), 5)

    def test_cotations_r01_r08(self):
        attendu = {"R01": 15, "R02": 12, "R03": 20, "R04": 9, "R05": 12, "R06": 10, "R07": 16, "R08": 12}
        r = repo.risks_df().set_index("id")
        self.assertEqual({k: int(r.score[k]) for k in attendu}, attendu)


class Dossiers(unittest.TestCase):
    def test_dossier_complet(self):
        a = analyze_dossier(db.SEED["dossiers"][0], date(2026, 11, 12))
        self.assertFalse(a["blocking"])
        self.assertEqual(a["completeness"]["rate"], 100)
        self.assertIn("aucun cas une décision d'octroi", a["disclaimer"])

    def test_dossier_incomplet(self):
        a = analyze_dossier(db.SEED["dossiers"][1], date(2026, 11, 12))
        self.assertTrue(a["blocking"])
        codes = {i["code"] for i in a["inconsistencies"]}
        self.assertTrue({"NAME_MISMATCH", "REVENUE_GAP", "DEBT_INCOH", "PRODUCT_DURATION", "CONCORDANCE"} <= codes)
        self.assertIn("R01", a["linked_risks"])


class Indicateurs(unittest.TestCase):
    def test_kpis(self):
        k = repo.kpis(repo.snapshot())
        self.assertEqual((k["total"], k["critical"], k["high"], k["covered_risks"], k["deficient_principles"]), (8, 2, 5, 8, 7))


class Permissions(unittest.TestCase):
    def test_separation_des_taches(self):
        self.assertFalse(auth.can("commercial", "risks.write"))
        self.assertTrue(auth.can("commercial", "anomalies.create"))
        self.assertFalse(auth.can("analyste", "users.manage"))
        self.assertTrue(auth.can("admin", "users.manage"))
        self.assertTrue(auth.check_password(db.SEED["demo_password"], db.query("select password_hash from users limit 1")[0]["password_hash"]))


class Assistant(unittest.TestCase):
    def test_reponse_locale_structuree(self):
        rep = offline_answer(repo.snapshot(), "Quels sont les risques prioritaires ? Donne des recommandations.")
        self.assertIn("RISQUE | LACUNE COSO | ACTION CORRECTIVE | RESPONSABLE | INDICATEUR DE SUIVI", rep)
        self.assertIn("R03", rep)

    def test_dossier_cible(self):
        rep = offline_answer(repo.snapshot(), "Analyse le dossier TPE-2026-002")
        self.assertIn("Incomplet", rep)
        self.assertIn("aucune décision d'octroi", rep)


class Exports(unittest.TestCase):
    def setUp(self):
        self.s = repo.snapshot()

    def test_pdfs(self):
        for fn in (exports.pdf_full, exports.pdf_executive, exports.pdf_coso, exports.pdf_heatmap, exports.pdf_action_plan):
            self.assertTrue(fn(self.s).startswith(b"%PDF"), fn.__name__)

    def test_excel_et_powerbi(self):
        self.assertTrue(exports.excel(self.s).startswith(b"PK"))
        z = zipfile.ZipFile(io.BytesIO(exports.powerbi_zip(self.s, "guide", "dax")))
        self.assertIn("DimRisque.csv", z.namelist())
        self.assertEqual(len(exports.powerbi_tables(self.s)), 13)


if __name__ == "__main__":
    unittest.main()
