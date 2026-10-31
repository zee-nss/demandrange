"""NASA POWER parsing, system sizing, unit economics and the published-data comparison (no internet)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

from demandrange.geo import osm, solar
from demandrange.sizing import CAPEX_PER_PERSON_USD, SizingAssumptions, cost_of_being_wrong, size_for_demand

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import compare_to_published as cmp  # noqa: E402

MONTHS = solar.MONTHS


def power_reply(values, units):
    vals = dict(zip(MONTHS, values)); vals["ANN"] = sum(values) / 12
    return {"properties": {"parameter": {"ALLSKY_SFC_SW_DWN": vals}}, "parameters": {"ALLSKY_SFC_SW_DWN": {"units": units}}}


def test_parse_kwh_and_mj_units_give_same_answer():
    kwh = [5.0, 5.2, 5.1, 4.8, 4.5, 4.3, 4.4, 4.9, 5.0, 4.8, 4.6, 4.7]
    a = solar.parse_power_climatology(power_reply(kwh, "kWh/m^2/day"))
    b = solar.parse_power_climatology(power_reply([v * 3.6 for v in kwh], "MJ/m^2/day"))
    assert a["worst_month_kwh_m2_day"] == b["worst_month_kwh_m2_day"] == 4.3 and a["worst_month"] == "JUN"
    with pytest.raises(osm.MapServiceError):
        solar.parse_power_climatology({"properties": {}})


def test_sizing_math():
    a = SizingAssumptions(customers=400, performance_ratio=0.75)
    s = size_for_demand(20, 5.0, a)                       # 8000 kWh a month
    assert s["daily_kwh"] == pytest.approx(8000 / 30.4)
    assert s["pv_kwp"] == pytest.approx(s["daily_kwh"] / (5.0 * 0.75))
    assert s["battery_kwh"] == pytest.approx(s["daily_kwh"] / 0.8)


def test_cost_of_being_wrong_uses_esmap_benchmark():
    assert CAPEX_PER_PERSON_USD == pytest.approx(259.2, abs=0.1)
    c = cost_of_being_wrong({"p10": 10, "p50": 16, "p90": 20}, SizingAssumptions(customers=400, persons_per_customer=5))
    assert c["persons_served"] == 2000
    assert c["capex_per_10pct_sizing_error_usd"] == pytest.approx(2000 * CAPEX_PER_PERSON_USD * 0.10)
    assert c["wasted_if_sized_for_high_case_usd"] == pytest.approx(c["benchmark_capex_usd"] * 0.2)


def test_forecast_and_api_include_sizing(monkeypatch):
    from fastapi.testclient import TestClient
    import api.main as api_main
    from demandrange.data import make_sample_dataset
    from demandrange.geo import features as feat
    from demandrange.model import DemandRangeModel
    model = DemandRangeModel().fit(make_sample_dataset(n_sites=80)); model.meta["data_source"] = "simulated"
    monkeypatch.setattr(api_main, "_model", model)
    f, w = feat.features_from_counts({"buildings": 300, "businesses": 36, "markets": 1, "schools_clinics": 2}, 20.0, energy_spend_usd=10)
    monkeypatch.setattr(feat, "features_from_coordinates", lambda *a, **k: (f, {"raw_counts": {"buildings": 300}, "warnings": w, "sources": ["test"], "radius_km": 2.0}))
    monkeypatch.setattr(solar, "solar_resource", lambda lat, lon: {"annual_kwh_m2_day": 5.2, "worst_month_kwh_m2_day": 4.4, "worst_month": "JUN", "source": "test"})
    body = TestClient(api_main.app).post("/forecast", json={"lat": 1, "lon": 29}).json()
    sz = body["system_sizing"]
    assert sz["sizes"]["high_case"]["pv_kwp"] > sz["sizes"]["low_case"]["pv_kwp"] > 0
    assert "What system the forecast implies" in body["memo_markdown"]
    monkeypatch.setattr(solar, "solar_resource", lambda lat, lon: (_ for _ in ()).throw(osm.MapServiceError("down")))
    body2 = TestClient(api_main.app).post("/forecast", json={"lat": 1, "lon": 29}).json()
    assert body2["system_sizing"] is None and any("Solar data unavailable" in x for x in body2["data_quality"]["warnings"])


def test_compare_to_published():
    from demandrange.data import make_sample_dataset
    from demandrange.geo import features as feat
    from demandrange.model import DemandRangeModel
    model = DemandRangeModel().fit(make_sample_dataset(n_sites=80))
    bench = pd.read_csv(Path(__file__).resolve().parent.parent / "data/benchmarks/drc_published_means.csv")
    f, w = feat.features_from_counts({"buildings": 300, "businesses": 36, "markets": 1, "schools_clinics": 2}, 20.0, energy_spend_usd=10)
    res = cmp.run(bench, model, lambda q: [{"lat": 0.0, "lon": 29.0}], lambda la, lo: (dict(f), {"raw_counts": {"buildings": 300}}))
    assert list(res["area"]) == ["Mutwanga", "Goma", "Lubero"] and (res["status"] == "ok").all()
    assert {"forecast_p50", "published_household_mean", "household_mean_inside_range"} <= set(res.columns)
