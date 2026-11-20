"""Tests de cohérence des paramètres utilisateur (étape 1)."""
from dataclasses import replace
from datetime import date

from config import AppParams


def test_default_params_are_valid():
    assert AppParams().validate() == []


def test_infeasible_max_weight_is_rejected():
    # 6 actifs × 15 % = 90 % < 100 % : aucune allocation ne peut sommer à 1
    p = replace(AppParams(), weight_max=0.15)
    assert any("infaisables" in e for e in p.validate())


def test_infeasible_min_weight_is_rejected():
    p = replace(AppParams(), weight_min=0.20)  # 6 × 20 % = 120 % > 100 %
    assert any("infaisables" in e for e in p.validate())


def test_dates_and_asset_count():
    p = replace(AppParams(), tickers=["AAPL"], start_date=date(2024, 1, 1), end_date=date(2023, 1, 1))
    errors = p.validate()
    assert any("2 actifs" in e for e in errors) and any("début doit précéder" in e for e in errors)


def test_split_date_must_be_inside_period():
    p = replace(AppParams(), split_date=date(2018, 6, 30))  # avant le début (01/01/2019)
    assert any("séparation" in e for e in p.validate())


def test_annualisation_factor():
    assert replace(AppParams(), frequency="Mensuelle").periods_per_year() == 12
    assert AppParams().periods_per_year() == 252
