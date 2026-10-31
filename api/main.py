"""DemandRange web API. Run locally with:  uvicorn api.main:app --reload --port 8000

Your Lovable or Bolt front end calls these endpoints. Docs page: /docs
"""
import json
import math
import os
import threading
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from demandrange import __version__
from demandrange.config import FEATURES, REPORT_DIR
from demandrange.finance import Assumptions
from demandrange.forecast import forecast_site
from demandrange.geo import features as feat
from demandrange.geo import grid, osm, solar
from demandrange.service import get_model, model_info

app = FastAPI(title="DemandRange API", version=__version__,
              description="Mini-grid demand forecasts with honest ranges, from real coordinates.")

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

_model = None
_lock = threading.Lock()
_heatmap_gate = threading.Semaphore(int(os.getenv("MAX_PARALLEL_HEATMAPS", "2")))


def model():
    global _model
    with _lock:
        if _model is None:
            _model = get_model()
    return _model


class AssumptionsIn(BaseModel):
    customers: int = 400
    capex_per_customer_usd: float = 600.0
    opex_per_customer_year_usd: float = 25.0
    tariff_usd_per_kwh: float = 0.45
    debt_share: float = 0.7
    interest_rate: float = 0.10
    tenor_years: int = 10
    target_dscr: float = 1.2


class ForecastRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    name: str = "Selected village"
    energy_spend_usd: Optional[float] = Field(None, ge=0, le=200,
                                              description="Monthly household spend on candles, kerosene, batteries, diesel")
    overrides: Optional[Dict[str, float]] = Field(None, description=f"Replace any map-derived input. Keys: {FEATURES}")
    skip_map_lookup: bool = Field(False, description="Use only `overrides` (all inputs needed except night_light and energy_spend_usd)")
    assumptions: Optional[AssumptionsIn] = None


class HeatmapRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    half_width_km: float = Field(8.0, ge=2, le=15)
    cells_per_side: int = Field(5, ge=2, le=6)
    metric: str = Field("p50", description="p10, p50, p90 or prob_cover_debt")
    year: Optional[int] = Field(None, ge=0, le=4, description="Years after connection; omit for the average of years 1 to 3")
    energy_spend_usd: Optional[float] = Field(None, ge=0, le=200)
    assumptions: Optional[AssumptionsIn] = None


def _clean(v):
    """Make numbers JSON-safe (NaN becomes null)."""
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _round_tree(x):
    if isinstance(x, dict):
        return {k: _round_tree(v) for k, v in x.items()}
    return round(x, 2) if isinstance(x, float) else x


def _assumptions(a):
    return Assumptions(**a.model_dump()) if a else Assumptions()


@app.get("/health")
def health():
    m = model()
    return {"status": "ok", "version": __version__, "model": model_info(m)}


@app.get("/geocode")
def geocode(q: str = Query(..., min_length=2, description="A place name, for example 'Kaduna, Nigeria'")):
    try:
        return {"results": osm.geocode(q)}
    except osm.MapServiceError as exc:
        raise HTTPException(503, str(exc))


@app.post("/forecast")
def forecast(req: ForecastRequest):
    m = model()
    notes, warnings, sources = [], [], []
    site, quality = {}, {}
    if not req.skip_map_lookup:
        try:
            site, quality = feat.features_from_coordinates(req.lat, req.lon, req.energy_spend_usd,
                                                           os.getenv("NIGHTLIGHT_TIF"))
        except osm.MapServiceError as exc:
            raise HTTPException(503, f"{exc} You can still forecast by sending skip_map_lookup=true with your own inputs.")
        sources, warnings = quality["sources"], list(quality["warnings"])
        notes.append(f"Looked up from coordinates ({req.lat:.4f}, {req.lon:.4f}) using: " + "; ".join(sources) + ".")
        notes.append(f"Raw counts within {quality['radius_km']} km: {quality['raw_counts']}.")
    else:
        site = {f: float("nan") for f in FEATURES}
        if req.energy_spend_usd is not None:
            site["energy_spend_usd"] = req.energy_spend_usd
    if req.overrides:
        bad = [k for k in req.overrides if k not in FEATURES]
        if bad:
            raise HTTPException(422, f"Unknown input(s): {bad}. Allowed: {FEATURES}")
        site.update(req.overrides)
        notes.append("You overrode: " + ", ".join(sorted(req.overrides)) + ".")
    required = [f for f in FEATURES if f not in ("night_light", "energy_spend_usd")]
    missing = [f for f in required if f not in site or (isinstance(site[f], float) and math.isnan(site[f]))]
    if missing:
        raise HTTPException(422, f"Missing inputs: {missing}. Provide them in `overrides`.")
    site["market_within_5km"] = int(site["market_within_5km"])
    site["schools_clinics"] = int(site["schools_clinics"])
    sun = None
    if not req.skip_map_lookup:
        try:
            sun = solar.solar_resource(req.lat, req.lon)
            notes.append("Sunshine from NASA POWER (about 0.5 degree grid).")
        except osm.MapServiceError as exc:
            warnings.append(f"Solar data unavailable, so system sizing was skipped. ({exc})")
    out = forecast_site(m, site, name=req.name, assumptions=_assumptions(req.assumptions), notes=notes, solar=sun)
    info = model_info(m)
    if info["warning"]:
        warnings.insert(0, info["warning"])
    return {
        "location": {"lat": req.lat, "lon": req.lon, "name": req.name},
        "site_inputs": {k: _clean(v) for k, v in site.items()},
        "data_quality": {"sources": sources, "warnings": warnings},
        "model_info": info,
        "curve": out["curve"].round(2).to_dict(orient="records"),
        "years_1_to_3_average": {k: round(v, 2) for k, v in out["years_avg"].items()},
        "productive_use": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out["productive_use"].items()},
        "finance": {k: round(v, 3) for k, v in out["finance"].items()},
        "drivers": out["drivers"].round(2).to_dict(orient="records"),
        "solar": sun,
        "system_sizing": _round_tree(out["sizing"]) if out["sizing"] else None,
        "memo_markdown": out["memo"],
    }


def _heatmap(req):
    if req.metric not in grid.METRICS:
        raise HTTPException(422, f"metric must be one of {list(grid.METRICS)}")
    if not _heatmap_gate.acquire(blocking=False):
        raise HTTPException(429, "Another heatmap is being built. Try again in a minute.")
    try:
        fc = grid.build_heatmap(model(), req.lat, req.lon, req.half_width_km, req.cells_per_side,
                                req.year, req.metric, req.energy_spend_usd, os.getenv("NIGHTLIGHT_TIF"),
                                _assumptions(req.assumptions))
    except osm.MapServiceError as exc:
        raise HTTPException(503, str(exc))
    finally:
        _heatmap_gate.release()
    info = model_info(model())
    fc["metadata"]["model_info"] = info
    fc["metadata"]["warnings"] = [info["warning"]] if info["warning"] else []
    return fc


@app.post("/heatmap")
def heatmap(req: HeatmapRequest):
    """GeoJSON grid of forecasts around a point. Each cell has p10, p50, p90 and `value`."""
    return _heatmap(req)


@app.post("/export/heatmap")
def export_heatmap(req: HeatmapRequest, format: str = Query("csv", pattern="^(csv|geojson)$")):
    fc = _heatmap(req)
    if format == "geojson":
        return Response(json.dumps(fc), media_type="application/geo+json",
                        headers={"Content-Disposition": "attachment; filename=demandrange_heatmap.geojson"})
    return Response(grid.heatmap_to_csv(fc), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=demandrange_heatmap.csv"})


@app.get("/validation")
def validation():
    p = REPORT_DIR / "validation.json"
    if not p.exists():
        raise HTTPException(404, "Run `python run_pipeline.py` to create validation results.")
    return {"model": model_info(model()), "results": json.loads(p.read_text())}


@app.get("/heatmap/presets")
def presets():
    """Pre-computed heatmaps (made by scripts/precompute_heatmap.py) load instantly."""
    d = REPORT_DIR.parent / "data" / "heatmaps"
    return {"presets": sorted(p.stem for p in d.glob("*.geojson"))} if d.exists() else {"presets": []}


@app.get("/heatmap/presets/{name}")
def preset(name: str):
    p = REPORT_DIR.parent / "data" / "heatmaps" / f"{os.path.basename(name)}.geojson"
    if not p.exists():
        raise HTTPException(404, "No such preset.")
    return json.loads(p.read_text())
