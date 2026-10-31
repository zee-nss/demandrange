"""Free solar data: NASA POWER (no key needed). Gives sunshine at a village.

NASA POWER's climatology service returns long-term monthly averages of the
sunlight reaching the ground (ALLSKY_SFC_SW_DWN). Its grid is about 0.5 degrees,
so nearby villages share a value. The units can be MJ or kWh per m2 per day
depending on the service version, so we read the units and convert.
"""
import os

import requests

from . import osm

POWER_URL = os.getenv("NASA_POWER_URL", "https://power.larc.nasa.gov/api/temporal/climatology/point")
PARAM = "ALLSKY_SFC_SW_DWN"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def parse_power_climatology(payload):
    """Read NASA POWER's reply. Returns sunlight in kWh per m2 per day (same number as 'peak sun hours')."""
    try:
        values = payload["properties"]["parameter"][PARAM]
    except (KeyError, TypeError):
        raise osm.MapServiceError("Unexpected NASA POWER reply (no solar values found).")
    monthly = {m: float(values[m]) for m in MONTHS if m in values and float(values[m]) > -900}
    if len(monthly) < 12:
        raise osm.MapServiceError("NASA POWER returned incomplete monthly values.")
    units = str((payload.get("parameters", {}).get(PARAM, {}) or {}).get("units", ""))
    annual = float(values.get("ANN", sum(monthly.values()) / 12))
    factor = 1 / 3.6 if ("MJ" in units.upper() or annual > 12) else 1.0   # MJ to kWh
    monthly = {m: v * factor for m, v in monthly.items()}
    return {"annual_kwh_m2_day": round(annual * factor, 2),
            "worst_month_kwh_m2_day": round(min(monthly.values()), 2),
            "worst_month": min(monthly, key=monthly.get),
            "source": "NASA POWER climatology (about 0.5 degree grid)"}


def solar_resource(lat, lon):
    """Fetch (and cache) the solar resource for a point."""
    key = f"power:{round(lat * 2) / 2},{round(lon * 2) / 2}"   # 0.5 degree grid
    hit = osm._cache_get(key)
    if hit is not None:
        return hit
    try:
        r = requests.get(POWER_URL, params={"parameters": PARAM, "community": "RE", "latitude": lat,
                                            "longitude": lon, "format": "JSON"},
                         headers={"User-Agent": osm.USER_AGENT}, timeout=(8, 30))
        r.raise_for_status()
        out = parse_power_climatology(r.json())
    except (requests.RequestException, ValueError) as exc:
        raise osm.MapServiceError(f"NASA POWER solar data is not reachable right now: {exc}")
    osm._cache_put(key, out)
    return out
