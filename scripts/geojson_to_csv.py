"""Turn a GeoJSON file of POINTS into the name,lat,lon CSV that the sanity check reads.

    python scripts/geojson_to_csv.py --input somalia_minigrids.geojson --output data/raw/known_minigrids.csv

GeoJSON stores coordinates as [longitude, latitude]. This script swaps them to
lat, lon for you. Pass --name-field if the file has a column with village names.
Files of lines (power lines, transmission networks) are not sites: the script
stops and tells you.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def convert(geo, name_field=None, prefix="site"):
    rows = []
    for i, f in enumerate(geo.get("features", []), start=1):
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            raise ValueError(f"Feature {i} is a {g.get('type')}, not a Point. This file holds lines or areas, not site locations.")
        lon, lat = g["coordinates"][:2]
        props = f.get("properties") or {}
        name = props.get(name_field) if name_field else None
        rows.append({"name": name or f"{prefix}_{i}", "lat": round(lat, 6), "lon": round(lon, 6)})
    if not rows:
        raise ValueError("No features found in the file.")
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="data/raw/known_minigrids.csv")
    ap.add_argument("--name-field")
    ap.add_argument("--prefix", default="minigrid")
    a = ap.parse_args()
    try:
        df = convert(json.loads(Path(a.input).read_text()), a.name_field, a.prefix)
    except (OSError, ValueError, KeyError) as exc:
        sys.exit(f"Could not convert: {exc}")
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.output, index=False)
    print(f"Wrote {len(df)} sites to {a.output}. Check the first rows:\n{df.head()}")


if __name__ == "__main__":
    main()
