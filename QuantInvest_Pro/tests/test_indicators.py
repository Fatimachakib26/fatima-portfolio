"""calculer_indicateurs : valeurs connues et traçabilité (les étapes redonnent la valeur)."""
import numpy as np
import pandas as pd
import pytest

from core.indicators import META, calculer_indicateurs, recalculer, tableau
from core.returns import periodic_rf
from tests.synthetic import synthetic_returns

R = synthetic_returns()
RES = calculer_indicateurs(R["A"], R["B"], 0.03, 252, poids=pd.Series([0.5, 0.3, 0.2]), rotation_totale=1.5)


def test_all_indicators_present():
    assert set(RES) == set(META)


@pytest.mark.parametrize("cle", list(META))
def test_traceability_recomputes_value(cle):
    res = RES[cle]
    assert abs(recalculer(res) - res.valeur) < 1e-10 * max(1, abs(res.valeur))
    assert res.etapes and res.formule and res.definition and res.n_obs == len(R)


def test_known_values():
    r, b = R["A"], R["B"]
    rf_p = periodic_rf(0.03)
    assert abs(RES["sharpe"].valeur - (r - rf_p).mean() / r.std() * np.sqrt(252)) < 1e-12
    assert abs(RES["beta"].valeur - r.cov(b) / b.var()) < 1e-12
    assert abs(RES["correlation_spy"].valeur - r.corr(b)) < 1e-12
    assert abs(RES["tracking_error"].valeur - (r - b).std() * np.sqrt(252)) < 1e-12
    assert abs(RES["nombre_effectif"].valeur - 1 / 0.38) < 1e-12
    from scipy.stats import kurtosis, skew
    assert abs(RES["asymetrie"].valeur - skew(r)) < 1e-12
    assert abs(RES["kurtosis"].valeur - kurtosis(r)) < 1e-12


def test_drawdown_duration_known_series():
    r = pd.Series([0.1, -0.5, 0.2, 1.0, 0.05], index=pd.bdate_range("2024-01-01", periods=5))
    res = calculer_indicateurs(r, None, 0.0)
    assert abs(res["drawdown_max"].valeur + 0.5) < 1e-12
    # pic après la 1re séance (1,1), creux 0,55, retour au-dessus de 1,1 à la 4e séance (1,32)
    assert res["duree_drawdown"].valeur == 3


def test_steps_mention_real_numbers():
    txt = " ".join(RES["sharpe"].etapes)
    assert RES["sharpe"].texte.split()[0] in txt


def test_table():
    t = tableau({"A": RES})
    assert t.loc["A", "Ratio de Sharpe"] == RES["sharpe"].valeur
