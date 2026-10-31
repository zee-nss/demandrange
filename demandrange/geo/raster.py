"""Optional: read night-time light from a free GeoTIFF you download once.

Where to get it: WorldPop Hub > Geospatial covariates > "Nighttime Lights
2015-2023", choose your country (free, ~100 m, annual radiance in nW/cm2/sr).
Save it and set the environment variable NIGHTLIGHT_TIF to its path.
If the file is missing, night light is simply left blank and the model copes.
"""
import math
import os


def sample_mean(lat, lon, radius_km=2.0, tif_path=None):
    """Average value inside a square around the point, or None if unavailable."""
    path = tif_path or os.getenv("NIGHTLIGHT_TIF")
    if not path or not os.path.exists(path):
        return None
    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        return None
    dlat = radius_km / 110.57
    dlon = radius_km / (111.32 * max(0.1, math.cos(math.radians(lat))))
    with rasterio.open(path) as src:
        win = from_bounds(lon - dlon, lat - dlat, lon + dlon, lat + dlat, src.transform)
        arr = src.read(1, window=win, boundless=True, masked=True)
        if arr.size == 0 or arr.mask.all():
            return None
        return float(arr.mean())
