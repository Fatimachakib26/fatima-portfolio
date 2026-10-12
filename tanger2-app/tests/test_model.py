"""Tests de non-régression : le moteur Python doit rester calé sur le modèle Excel (onglet 21_Comparaison)."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import model as M  # noqa: E402

# valeurs de l'Excel (cas central) : VAN (MDH), TRI projet, TRI FP, WACC, DSCR min, levier max
EXCEL = {
    "A": (107.5, 0.1298, 0.1541, 0.1051, 1.58, 1.33),
    "B": (114.2, 0.1298, 0.1720, 0.1037, 1.37, 1.73),
    "C": (272.5, 0.1686, 0.2241, 0.1035, 1.64, 1.47),
}


@pytest.mark.parametrize("sc", "ABC")
def test_calibrage_excel(sc):
    k = M.run(M.SCENARIOS[sc])["kpi"]
    van, tri, tri_fp, wacc, dscr, lev = EXCEL[sc]
    assert k["VAN projet"] == pytest.approx(van, abs=8)
    assert k["TRI projet"] == pytest.approx(tri, abs=0.003)
    assert k["TRI FP"] == pytest.approx(tri_fp, abs=0.004)
    assert k["WACC"] == pytest.approx(wacc, abs=0.0005)
    assert k["DSCR min"] == pytest.approx(dscr, abs=0.03)
    assert k["Levier max"] == pytest.approx(lev, abs=0.1)


@pytest.mark.parametrize("sc", "ABC")
def test_cas_central_finance_et_conforme(sc):
    k = M.run(M.SCENARIOS[sc])["kpi"]
    assert k["Trésorerie min"] >= 0
    assert k["Covenants OK"]


def test_business_plan_croisiere():
    t = M.run(M.SCENARIOS["B"])["table"]
    i = list(t["Année"]).index(2032)
    assert t["Chiffre d'affaires"][i] == pytest.approx(1560.9, abs=0.5)
    assert t["EBITDA économique"][i] == pytest.approx(263.5, abs=0.5)


def test_stress_et_mesures():
    """Le stress combiné casse le montage B ; le paquet de mesures du cas 7 le rend soutenable."""
    stress = M.run(M.SCENARIOS["B"], M.CASES["6. Stress combiné"])["kpi"]
    assert stress["VAN projet"] < 0
    assert stress["Besoin non financé"] > 100
    assert stress["DSCR min"] < M.DSCR_COVENANT
    fixed = M.run(M.SCENARIOS["B"], M.CASES["7. Combiné + mesures"])["kpi"]
    assert fixed["Covenants OK"]
    assert fixed["Trésorerie min"] >= 0


def test_retard_degrade_le_dscr():
    base = M.run(M.SCENARIOS["B"])["kpi"]["DSCR min"]
    late = M.run(M.SCENARIOS["B"], M.Shocks(delay_months=6))["kpi"]["DSCR min"]
    assert late < base


def test_monte_carlo_reproductible():
    vol = {"price": 0.02, "volume": 0.06, "materials": 0.03, "energy": 0.1, "rate": 0.005,
           "delay_mean": 2.0, "capex_tri": (-0.03, 0.0, 0.25)}
    a = M.monte_carlo(M.SCENARIOS["B"], M.Shocks(), M.Market(), M.draw_mc(50, vol, seed=1))
    b = M.monte_carlo(M.SCENARIOS["B"], M.Shocks(), M.Market(), M.draw_mc(50, vol, seed=1))
    assert [r["VAN projet"] for r in a] == [r["VAN projet"] for r in b]
    assert all(math.isfinite(r["VAN projet"]) for r in a)


def test_irr():
    assert M.irr([-100, 110]) == pytest.approx(0.10, abs=1e-6)
