"""Free OpenStreetMap services: Overpass (map features) and Nominatim (place search).

Both are free and need no API key, but they are shared community services.
Be polite: results are cached on disk, requests are spaced out, and we send a
real User-Agent. Set GEO_CONTACT to your email so the operators can reach you.
"""
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path

import requests

OVERPASS_URLS = [u for u in [
    os.getenv("OVERPASS_URL"),
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
] if u]
NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
USER_AGENT = f"DemandRange/0.2 (Global Energy Hackathon; contact: {os.getenv('GEO_CONTACT', 'set-GEO_CONTACT')})"
CACHE_DIR = Path(os.getenv("DEMANDRANGE_CACHE", Path(tempfile.gettempdir()) / "demandrange_cache"))
CACHE_TTL_S = 30 * 24 * 3600

BUSINESS_AMENITIES = "marketplace|restaurant|bar|cafe|fast_food|bank|pharmacy|bureau_de_change|mobile_money_agent|car_wash|fuel"
HEALTH_EDU = "school|college|clinic|hospital|doctors|health_post"


class MapServiceError(RuntimeError):
    """Raised when the free map services cannot be reached."""


# ---------------------------------------------------------------- queries
def counts_query(lat, lon, radius_m=2000, wide_m=5000):
    """One request that returns four counts, in this order:
    buildings, businesses (within radius_m), markets, schools+clinics (within wide_m)."""
    a, w = f"(around:{radius_m},{lat},{lon})", f"(around:{wide_m},{lat},{lon})"
    return f"""[out:json][timeout:60];
way["building"]{a};
out count;
(
  nwr["shop"]{a};
  nwr["craft"]{a};
  nwr["amenity"~"^({BUSINESS_AMENITIES})$"]{a};
);
out count;
nwr["amenity"="marketplace"]{w};
out count;
nwr["amenity"~"^({HEALTH_EDU})$"]{w};
out count;
"""


def lines_query(lat, lon, radius_m):
    return f"""[out:json][timeout:90];
way["power"~"^(line|minor_line)$"](around:{radius_m},{lat},{lon});
out geom;
"""


# ---------------------------------------------------------------- parsing
def parse_counts(payload):
    """Read the four counts from an Overpass response."""
    counts = [int(e["tags"]["total"]) for e in payload.get("elements", [])
              if e.get("type") == "count"]
    if len(counts) != 4:
        raise MapServiceError(f"Unexpected Overpass reply: expected 4 counts, got {len(counts)}")
    return {"buildings": counts[0], "businesses": counts[1],
            "markets": counts[2], "schools_clinics": counts[3]}


def parse_lines(payload):
    """Return power lines as lists of (lat, lon) points."""
    lines = []
    for e in payload.get("elements", []):
        geom = e.get("geometry")
        if e.get("type") == "way" and geom:
            lines.append([(p["lat"], p["lon"]) for p in geom])
    return lines


# ---------------------------------------------------------------- geometry
def _to_xy_km(lat, lon, lat0, lon0):
    kx = 111.32 * math.cos(math.radians(lat0))
    return (lon - lon0) * kx, (lat - lat0) * 110.57


def nearest_line_km(lat, lon, lines):
    """Distance in km from a point to the closest power line (None if no lines)."""
    best = None
    for pts in lines:
        xy = [_to_xy_km(p[0], p[1], lat, lon) for p in pts]
        for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
            dx, dy = x2 - x1, y2 - y1
            seg = dx * dx + dy * dy
            t = 0.0 if seg == 0 else max(0.0, min(1.0, -(x1 * dx + y1 * dy) / seg))
            d = math.hypot(x1 + t * dx, y1 + t * dy)
            best = d if best is None else min(best, d)
        if len(xy) == 1:
            d = math.hypot(*xy[0])
            best = d if best is None else min(best, d)
    return best


# ---------------------------------------------------------------- network
def _cache_path(key):
    return CACHE_DIR / (hashlib.sha1(key.encode()).hexdigest() + ".json")


def _cache_get(key):
    p = _cache_path(key)
    if p.exists() and time.time() - p.stat().st_mtime < CACHE_TTL_S:
        return json.loads(p.read_text())
    return None


def _cache_put(key, value):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(key).write_text(json.dumps(value))
    except OSError:
        pass  # caching is a bonus, never a failure


def reachable(timeout=8):
    """Quick check that a free Overpass server answers. Returns (True, url) or (False, reason)."""
    last = "no Overpass address configured"
    for url in OVERPASS_URLS:
        try:
            r = requests.get(url.replace("/interpreter", "/status"), headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if r.status_code == 200:
                return True, url
            last = f"{url} answered HTTP {r.status_code}"
        except requests.RequestException as exc:
            last = f"{url}: {exc.__class__.__name__}"
    return False, last


def overpass(query, retries=1, pause=2.0):
    """Run an Overpass query (cached). Tries each mirror, then raises MapServiceError."""
    hit = _cache_get("overpass:" + query)
    if hit is not None:
        return hit
    last = None
    for url in OVERPASS_URLS:
        for attempt in range(retries + 1):
            try:
                r = requests.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=(8, 70))
                if r.status_code == 200:
                    data = r.json()
                    _cache_put("overpass:" + query, data)
                    return data
                last = f"{url} returned HTTP {r.status_code}"
            except (requests.RequestException, ValueError) as exc:
                last = f"{url}: {exc}"
            time.sleep(pause * (attempt + 1))
    raise MapServiceError(f"OpenStreetMap (Overpass) is not reachable right now. Last error: {last}")


_last_nominatim = [0.0]


def geocode(query, limit=5):
    """Place name -> coordinates, using free Nominatim (max 1 request per second)."""
    hit = _cache_get("nominatim:" + query)
    if hit is not None:
        return hit
    wait = 1.1 - (time.time() - _last_nominatim[0])
    if wait > 0:
        time.sleep(wait)
    try:
        r = requests.get(NOMINATIM_URL, params={"q": query, "format": "jsonv2", "limit": limit},
                         headers={"User-Agent": USER_AGENT}, timeout=(8, 25))
        _last_nominatim[0] = time.time()
        r.raise_for_status()
        out = [{"name": x["display_name"], "lat": float(x["lat"]), "lon": float(x["lon"])} for x in r.json()]
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise MapServiceError(f"Place search (Nominatim) is not reachable right now: {exc}")
    _cache_put("nominatim:" + query, out)
    return out
