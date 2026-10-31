"""Tests for map lookups, heatmap, API and the real-data builder.
No internet needed: map responses are replaced with recorded samples."""
import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from demandrange.config import FEATURES, REQUIRED_COLUMNS
from demandrange.data import make_sample_dataset
from demandrange.geo import features as feat
from demandrange.geo import grid, osm
from demandrange.model import DemandRangeModel

COUNTS_REPLY = {"elements": [
    {"type": "count", "tags": {"total": "320"}},
    {"type": "count", "tags": {"total": "41"}},
    {"type": "count", "tags": {"total": "1"}},
    {"type": "count", "tags": {"total": "3"}},
]}
LINE_REPLY = {"elements": [{"type": "way", "geometry": [
    {"lat": 0.0, "lon": -1.0}, {"lat": 0.0, "lon": 1.0}]}]}


def fake_extract(lat, lon, *a, **k):
    f, w = feat.features_from_counts({"buildings": 300, "businesses": 36, "markets": 1,
                                      "schools_clinics": 2}, grid_km=20.0, energy_spend_usd=10)
    return f, {"raw_counts": {"buildings": 300}, "warnings": w, "sources": ["test"], "radius_km": 2.0}


@pytest.fixture(scope="module")
def model():
    m = DemandRangeModel().fit(make_sample_dataset(n_sites=120))
    m.meta["data_source"] = "simulated"
    return m


def test_parse_counts():
    assert osm.parse_counts(COUNTS_REPLY) == {"buildings": 320, "businesses": 41, "markets": 1, "schools_clinics": 3}
    with pytest.raises(osm.MapServiceError):
        osm.parse_counts({"elements": []})


def test_nearest_line_distance():
    lines = osm.parse_lines(LINE_REPLY)
    d = osm.nearest_line_km(0.1, 0.0, lines)      # 0.1 degree of latitude north of the line
    assert d == pytest.approx(11.06, abs=0.2)
    assert osm.nearest_line_km(0.1, 0.0, []) is None


def test_features_from_counts_and_warnings():
    f, w = feat.features_from_counts({"buildings": 400, "businesses": 40, "markets": 2, "schools_clinics": 9}, 12.3)
    assert f["business_per_100"] == pytest.approx(10.0)
    assert f["market_within_5km"] == 1 and f["schools_clinics"] == 6
    assert math.isnan(f["night_light"]) and any("Night-time" in x for x in w)
    f2, w2 = feat.features_from_counts({"buildings": 4, "businesses": 1, "markets": 0, "schools_clinics": 0}, 80)
    assert any("incomplete" in x for x in w2)


def test_model_handles_missing_inputs(model):
    base = dict(households=400, business_per_100=10, night_light=0.5, dist_to_grid_km=20,
                market_within_5km=1, schools_clinics=1, energy_spend_usd=10, years_since_connection=2)
    full = model.predict(pd.DataFrame([base])).iloc[0]
    blank = model.predict(pd.DataFrame([{**base, "night_light": float("nan"), "energy_spend_usd": float("nan")}])).iloc[0]
    assert not blank.isna().any()
    assert (blank["p90"] - blank["p10"]) >= (full["p90"] - full["p10"]) - 1e-9   # wider when less is known


def test_small_data_model_still_calibrates():
    small = make_sample_dataset(n_sites=10)
    m = DemandRangeModel().fit(small)
    assert m.meta["small_data"] is True and max(m.widen.values()) > 0


def test_grid_and_heatmap(model):
    cells = grid.make_cells(10.0, 7.0, 8, 4)
    assert len(cells) == 16 and cells[0]["bounds"][0] < cells[-1]["bounds"][2]
    fc = grid.build_heatmap(model, 10.0, 7.0, 8, 3, extract=fake_extract)
    assert fc["metadata"]["cells_ok"] == 9 and len(fc["features"]) == 9
    assert "p50" in fc["features"][0]["properties"]
    assert grid.heatmap_to_csv(fc).startswith("cell_id,")
    fc2 = grid.build_heatmap(model, 10.0, 7.0, 8, 2, metric="prob_cover_debt", extract=fake_extract)
    assert fc2["metadata"]["unit"] == "probability"


@pytest.fixture()
def client(model, monkeypatch):
    import api.main as api_main
    monkeypatch.setattr(api_main, "_model", model)
    monkeypatch.setattr(feat, "features_from_coordinates", lambda lat, lon, spend=None, tif=None, lines=None: fake_extract(lat, lon))
    monkeypatch.setattr(grid, "fetch_lines_once", lambda *a, **k: [])
    from demandrange.geo import solar as _solar
    monkeypatch.setattr(_solar, "solar_resource", lambda lat, lon: {"annual_kwh_m2_day": 5.0, "worst_month_kwh_m2_day": 4.2, "worst_month": "JUN", "source": "test"})
    return TestClient(api_main.app)


def test_api_health_and_forecast(client):
    h = client.get("/health").json()
    assert h["status"] == "ok" and h["model"]["trained_on_simulated_data"] is True
    r = client.post("/forecast", json={"lat": 10.5, "lon": 7.4, "name": "Test"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["curve"]) == 5 and body["curve"][0]["p10"] <= body["curve"][0]["p90"]
    assert body["model_info"]["warning"] and "SIMULATED" in body["data_quality"]["warnings"][0]
    assert "memo_markdown" in body and "Where the inputs came from" in body["memo_markdown"]


def test_api_manual_inputs_and_errors(client):
    manual = {"lat": 0, "lon": 0, "skip_map_lookup": True, "overrides": {
        "households": 500, "business_per_100": 12, "dist_to_grid_km": 25,
        "market_within_5km": 1, "schools_clinics": 2}}
    assert client.post("/forecast", json=manual).status_code == 200
    assert client.post("/forecast", json={"lat": 0, "lon": 0, "skip_map_lookup": True}).status_code == 422
    assert client.post("/forecast", json={"lat": 0, "lon": 0, "overrides": {"nonsense": 1}}).status_code == 422
    assert client.post("/forecast", json={"lat": 95, "lon": 0}).status_code == 422


def test_api_heatmap_and_exports(client):
    body = {"lat": 10.5, "lon": 7.4, "cells_per_side": 3, "half_width_km": 6}
    fc = client.post("/heatmap", json=body).json()
    assert fc["type"] == "FeatureCollection" and fc["metadata"]["cells_ok"] == 9
    csv_r = client.post("/export/heatmap?format=csv", json=body)
    assert csv_r.status_code == 200 and csv_r.text.startswith("cell_id")
    gj = client.post("/export/heatmap?format=geojson", json=body)
    assert gj.json()["type"] == "FeatureCollection"
    assert client.post("/heatmap", json={**body, "metric": "bogus"}).status_code == 422


def test_api_reports_map_outage(client, monkeypatch):
    def boom(*a, **k):
        raise osm.MapServiceError("down")
    monkeypatch.setattr(feat, "features_from_coordinates", boom)
    r = client.post("/forecast", json={"lat": 1, "lon": 1})
    assert r.status_code == 503 and "skip_map_lookup" in r.json()["detail"]


def test_build_training_table_both_layouts():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import build_training_table as btt

    extract = lambda la, lo, sp: fake_extract(la, lo)
    a = pd.DataFrame({"site_id": ["s1", "s1", "s2"], "lat": [1, 1, 2], "lon": [1, 1, 2],
                      "years_since_connection": [0, 1, 0], "kwh_per_customer_month": [10, 12, 14]})
    t, skipped = btt.build_table(a, extract)
    assert list(t.columns) == REQUIRED_COLUMNS and len(t) == 3 and skipped.empty
    b = pd.DataFrame({"site_id": ["s1"] * 24, "lat": 1.0, "lon": 1.0, "connection_date": "2023-01-01",
                      "month": pd.date_range("2023-01-01", periods=24, freq="MS").astype(str),
                      "kwh_total": 4000.0, "customers": 400})
    t2, _ = btt.build_table(b, extract)
    assert sorted(t2["years_since_connection"]) == [0, 1] and (t2["kwh_per_customer_month"] == 10).all()

    def flaky(la, lo, sp):
        if la == 2:
            raise osm.MapServiceError("no data")
        return fake_extract(la, lo)
    t3, skipped3 = btt.build_table(a, flaky)
    assert len(skipped3) == 1 and "s2" not in set(t3["site_id"])
