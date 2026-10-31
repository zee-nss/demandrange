"""Run with:  pytest -q   (every test should pass before you record your demo)"""
from pathlib import Path

import pandas as pd
import pytest

from demandrange.config import MODEL_COLUMNS, REQUIRED_COLUMNS, TARGET
from demandrange.data import load_sites_csv, make_sample_dataset
from demandrange.finance import Assumptions, breakeven_kwh, prob_demand_above
from demandrange.forecast import forecast_site
from demandrange.model import DemandRangeModel
from demandrange.productive_use import cost_index


@pytest.fixture(scope="module")
def df():
    return make_sample_dataset(n_sites=120)


@pytest.fixture(scope="module")
def model(df):
    return DemandRangeModel().fit(df)


def test_dataset_has_required_columns(df):
    assert set(REQUIRED_COLUMNS).issubset(df.columns)
    assert df[TARGET].between(3, 40).all()


def test_ranges_are_ordered(model, df):
    p = model.predict(df.head(50))
    assert (p["p10"] <= p["p50"]).all() and (p["p50"] <= p["p90"]).all()


def test_demand_grows_after_connection(model):
    site = dict(households=500, business_per_100=15, night_light=0.8, dist_to_grid_km=20,
                market_within_5km=1, schools_clinics=2, energy_spend_usd=12)
    out = forecast_site(model, site)
    c = out["curve"]
    assert c.loc[c.year == 3, "p50"].iloc[0] > c.loc[c.year == 0, "p50"].iloc[0]


def test_productive_use_matches_brief():
    assert cost_index(0.22) == pytest.approx(1.0)
    assert cost_index(0.40) == pytest.approx(0.75)   # the 25% cut in the brief


def test_finance_logic():
    a = Assumptions()
    be = breakeven_kwh(a)
    assert be > 0
    # Higher forecast -> higher chance of covering the loan
    low = prob_demand_above(10, 12, 15, be)
    high = prob_demand_above(20, 25, 30, be)
    assert high > low
    # Cheaper tariff -> need more kWh
    assert breakeven_kwh(Assumptions(tariff_usd_per_kwh=0.30)) > be


def test_loader_rejects_bad_csv(tmp_path):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"site_id": ["a"], "region": ["x"]}).to_csv(bad, index=False)
    with pytest.raises(ValueError):
        load_sites_csv(bad)


def test_app_runs_without_errors():
    from streamlit.testing.v1 import AppTest
    app_path = str(Path(__file__).resolve().parent.parent / "app.py")
    at = AppTest.from_file(app_path, default_timeout=120).run()
    assert not at.exception
