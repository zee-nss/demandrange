"""One coordinate in, the model's village features out (plus honest warnings)."""
import math

from . import osm, raster

NAN = float("nan")
RADIUS_KM = 2.0       # the village area we count buildings and shops in
LINE_RADII_M = (10_000, 30_000, 80_000)   # widen the power-line search in steps
MAX_GRID_DISTANCE_KM = 80.0


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def find_grid_distance_km(lat, lon, lines=None):
    """Distance to the nearest mapped power line. Searches wider until it finds one."""
    if lines is not None:
        d = osm.nearest_line_km(lat, lon, lines)
        return MAX_GRID_DISTANCE_KM if d is None else min(d, MAX_GRID_DISTANCE_KM)
    for r in LINE_RADII_M:
        found = osm.parse_lines(osm.overpass(osm.lines_query(lat, lon, r)))
        d = osm.nearest_line_km(lat, lon, found)
        if d is not None:
            return min(d, MAX_GRID_DISTANCE_KM)
    return MAX_GRID_DISTANCE_KM


def features_from_counts(counts, grid_km, night_light=None, energy_spend_usd=None):
    """Pure function (no network): turn raw counts into model features + warnings."""
    b = counts["buildings"]
    warnings = []
    if b < 20:
        warnings.append("Very few buildings are mapped here. OpenStreetMap may be "
                        "incomplete, so the forecast is less reliable. Check the "
                        "area on the map and override the inputs if you can.")
    business = counts["businesses"] / b * 100 if b >= 10 else NAN
    if math.isnan(business):
        business = _clip(counts["businesses"], 0, 40)  # tiny sample: use raw count
    feats = {
        "households": float(max(b, 1)),
        "business_per_100": float(_clip(business, 0, 40)),
        "night_light": NAN if night_light is None else float(_clip(night_light, 0, 3)),
        "dist_to_grid_km": float(grid_km),
        "market_within_5km": int(counts["markets"] > 0),
        "schools_clinics": int(min(counts["schools_clinics"], 6)),
        "energy_spend_usd": NAN if energy_spend_usd is None else float(energy_spend_usd),
    }
    if night_light is None:
        warnings.append("Night-time light was not available, so the range is a little wider.")
    if energy_spend_usd is None:
        warnings.append("Household energy spend was not provided, so the range is a little wider.")
    return feats, warnings


def features_from_coordinates(lat, lon, energy_spend_usd=None, nightlight_tif=None,
                              lines=None):
    """Look up a village from its coordinates. Returns (features, quality dict)."""
    counts = osm.parse_counts(osm.overpass(osm.counts_query(lat, lon, int(RADIUS_KM * 1000))))
    grid_km = find_grid_distance_km(lat, lon, lines)
    light = raster.sample_mean(lat, lon, RADIUS_KM, nightlight_tif)
    feats, warnings = features_from_counts(counts, grid_km, light, energy_spend_usd)
    quality = {
        "raw_counts": counts,
        "radius_km": RADIUS_KM,
        "sources": ["OpenStreetMap (buildings, shops, markets, schools, clinics, power lines)"]
                   + (["Night-time light GeoTIFF"] if light is not None else []),
        "warnings": warnings,
    }
    return feats, quality
