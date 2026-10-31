"""Heatmap: forecast a grid of cells around a point and return GeoJSON."""
import csv
import io
import math
from concurrent.futures import ThreadPoolExecutor

from ..finance import Assumptions, finance_summary
from ..forecast import DEFAULT_SPEND_USD, growth_curve
from . import features as feat
from . import osm

METRICS = ("p10", "p50", "p90", "prob_cover_debt")


def make_cells(lat, lon, half_width_km, cells_per_side):
    """Split a square (centred on lat, lon) into cells_per_side x cells_per_side cells."""
    dlat = half_width_km / 110.57
    dlon = half_width_km / (111.32 * max(0.1, math.cos(math.radians(lat))))
    south, west = lat - dlat, lon - dlon
    step_lat, step_lon = 2 * dlat / cells_per_side, 2 * dlon / cells_per_side
    cells = []
    for r in range(cells_per_side):
        for c in range(cells_per_side):
            s, w = south + r * step_lat, west + c * step_lon
            cells.append({"id": f"r{r}c{c}", "lat": s + step_lat / 2, "lon": w + step_lon / 2,
                          "bounds": (s, w, s + step_lat, w + step_lon)})
    return cells


def fetch_lines_once(lat, lon, half_width_km):
    """One power-line request covering the whole grid (cheaper than one per cell)."""
    for extra_km in (10, 30, 80):
        radius_m = int((half_width_km * 1.42 + extra_km) * 1000)
        lines = osm.parse_lines(osm.overpass(osm.lines_query(lat, lon, radius_m)))
        if lines:
            return lines
    return []


def build_heatmap(model, lat, lon, half_width_km=8.0, cells_per_side=5, year=None,
                  metric="p50", energy_spend_usd=None, nightlight_tif=None,
                  assumptions=None, extract=None, lines=None, workers=3):
    """Forecast every cell. `extract(lat, lon)` can be swapped in for tests."""
    if metric not in METRICS:
        raise ValueError(f"metric must be one of {METRICS}")
    assumptions = assumptions or Assumptions()
    cells = make_cells(lat, lon, half_width_km, cells_per_side)
    if extract is None:
        if lines is None:
            lines = fetch_lines_once(lat, lon, half_width_km)

        def extract(la, lo):
            return feat.features_from_coordinates(la, lo, energy_spend_usd, nightlight_tif, lines=lines)

    def work(cell):
        try:
            return cell, extract(cell["lat"], cell["lon"]), None
        except osm.MapServiceError as exc:
            return cell, None, str(exc)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(work, cells))

    features, failed, values = [], 0, []
    spend_for_bill = energy_spend_usd if energy_spend_usd is not None else DEFAULT_SPEND_USD
    for cell, got, err in results:
        s, w, n, e = cell["bounds"]
        ring = [[w, s], [e, s], [e, n], [w, n], [w, s]]
        props = {"cell_id": cell["id"], "center_lat": round(cell["lat"], 5), "center_lon": round(cell["lon"], 5)}
        if got is None:
            failed += 1
            props.update({"status": "failed", "error": err, "value": None})
        else:
            site, quality = got
            curve = growth_curve(model, site)
            first3 = curve[curve["year"].between(1, 3)]
            avg = {k: float(first3[k].mean()) for k in ("p10", "p50", "p90")}
            fin = finance_summary(avg, assumptions, spend_for_bill)
            row = (curve[curve["year"] == year].iloc[0] if year is not None else None)
            shown = {k: float(row[k]) if row is not None else avg[k] for k in ("p10", "p50", "p90")}
            value = fin["prob_cover_debt"] if metric == "prob_cover_debt" else shown[metric]
            values.append(value)
            props.update({
                "status": "ok", "value": round(value, 3),
                "p10": round(shown["p10"], 2), "p50": round(shown["p50"], 2), "p90": round(shown["p90"], 2),
                "prob_cover_debt": round(fin["prob_cover_debt"], 3),
                "households": site["households"], "business_per_100": round(site["business_per_100"], 1),
                "dist_to_grid_km": round(site["dist_to_grid_km"], 1),
                "market_within_5km": site["market_within_5km"], "schools_clinics": site["schools_clinics"],
                "buildings_mapped": quality["raw_counts"]["buildings"] if "raw_counts" in quality else None,
                "warnings": quality.get("warnings", []),
            })
        features.append({"type": "Feature", "properties": props,
                         "geometry": {"type": "Polygon", "coordinates": [ring]}})
    if not values:
        raise osm.MapServiceError("Could not read map data for any cell. Try again later or use manual inputs.")
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "metric": metric,
            "year": year if year is not None else "average of years 1 to 3",
            "unit": "probability" if metric == "prob_cover_debt" else "kWh per customer per month",
            "min": round(min(values), 3), "max": round(max(values), 3),
            "cells_ok": len(values), "cells_failed": failed,
            "center": {"lat": lat, "lon": lon}, "half_width_km": half_width_km,
        },
    }


def heatmap_to_csv(fc):
    cols = ["cell_id", "center_lat", "center_lon", "status", "p10", "p50", "p90", "prob_cover_debt",
            "households", "business_per_100", "dist_to_grid_km", "market_within_5km", "schools_clinics"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for f in fc["features"]:
        w.writerow(f["properties"])
    return buf.getvalue()
