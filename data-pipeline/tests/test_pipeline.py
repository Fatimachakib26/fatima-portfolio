"""Tests du pipeline (à lancer après `python run.py`) : python -m unittest discover -s tests"""
import gzip
import json
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MARTS = json.loads((ROOT / "data" / "marts" / "sba_marts.json").read_text(encoding="utf-8"))
SUMMARY = json.loads((ROOT / "reports" / "cleaning_summary.json").read_text(encoding="utf-8"))


class Pipeline(unittest.TestCase):
    def test_reconciliation(self):
        self.assertEqual(SUMMARY["raw_rows"], SUMMARY["clean_rows"] + SUMMARY["rejected_rows"])

    def test_manifest_integrity(self):
        import hashlib
        man = json.loads((RAW / "MANIFEST.json").read_text(encoding="utf-8"))
        for e in man["files"].values():
            h = hashlib.sha256((RAW / e["name"]).read_bytes()).hexdigest()
            self.assertEqual(h, e["sha256"], e["name"])

    def test_no_personal_data_in_clean_layer(self):
        with gzip.open(ROOT / "data" / "clean" / "loans_clean.csv.gz", "rt", encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        for col in ["BorrName", "BorrStreet", "BorrZip"]:
            self.assertNotIn(col, header)

    def test_default_rate_matches_independent_recount(self):
        raw = pd.read_csv(RAW / MARTS["files"]["loans"]["name"], dtype=str, keep_default_na=False, usecols=None).drop_duplicates()
        st = raw["LoanStatus"].str.replace(" ", "")
        independent = (st == "CHGOFF").sum() / ((st == "CHGOFF") | (st == "PIF")).sum()
        self.assertAlmostEqual(MARTS["overview"]["default_rate"], independent, places=3)

    def test_marts_add_up(self):
        o = MARTS["overview"]
        for t in ["by_cohort", "by_sector", "by_size", "by_term"]:
            rows = MARTS["tables"][t]
            self.assertEqual(sum(r["resolved"] for r in rows), o["loans_resolved"], t)
            self.assertEqual(sum(r["defaults"] for r in rows), o["defaults"], t)
        self.assertAlmostEqual(sum(r["share"] for r in MARTS["tables"]["time_to_default"]), 1.0, places=4)  # parts arrondies à 6 décimales dans le JSON

    def test_rates_are_probabilities(self):
        for t, rows in MARTS["tables"].items():
            for r in rows:
                for k in ("default_rate", "loss_rate"):
                    if r.get(k) is not None:
                        self.assertTrue(0 <= r[k] <= 1, (t, r))


if __name__ == "__main__":
    unittest.main()
