"""Plausibility check on REAL mini-grid locations (no metered data needed).

    python scripts/sanity_check_known_sites.py --input data/raw/known_minigrids.csv

Input: a CSV with columns  name,lat,lon  (latitude/longitude and lng also work).
Use REAL OFF-GRID MINI-GRID locations, for example the Somalia or Kenya files on
energydata.info. Towns on the national grid or power-line nodes are NOT mini-grids
and will give meaningless results.

Handy options:
  --limit 5      try only the first 5 sites first (do this before the full run)
  --force        run even if the map services look unreachable

The script forecasts each location from the map and reports how many land inside
the 5 to 35 kWh band that ESMAP found. It checks plausibility, not accuracy.
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ALIASES = {"name": ["name", "site", "site_id", "village", "locality"],
           "lat": ["lat", "latitude", "y"], "lon": ["lon", "lng", "long", "longitude", "x"]}


def load_sites(path, limit=None):
    """Read the CSV, tolerate common column names, drop empty and repeated points."""
    p = Path(path)
    if not p.exists():
        near = sorted(str(q) for q in Path(p.parent if str(p.parent) != "." else ".").glob("*.csv"))[:8] if p.parent.exists() else []
        hint = ("\nCSV files I can see there: " + ", ".join(near)) if near else "\nThe folder does not exist yet. Create it and put your CSV inside."
        raise FileNotFoundError(f"Cannot find '{path}'. Check the file name and folder (run the command from the project folder).{hint}")
    df = pd.read_csv(p)
    cols = {c.lower().strip(): c for c in df.columns}
    pick = {}
    for want, options in ALIASES.items():
        found = next((cols[o] for o in options if o in cols), None)
        if found is None and want != "name":
            raise ValueError(f"No '{want}' column. Columns in your file: {list(df.columns)}")
        pick[want] = found
    out = pd.DataFrame({"name": df[pick["name"]] if pick["name"] else [f"site_{i + 1}" for i in range(len(df))],
                        "lat": pd.to_numeric(df[pick["lat"]], errors="coerce"),
                        "lon": pd.to_numeric(df[pick["lon"]], errors="coerce")})
    out = out.dropna(subset=["lat", "lon"])
    out = out[out["lat"].between(-90, 90) & out["lon"].between(-180, 180)]
    out = out.drop_duplicates(["lat", "lon"]).reset_index(drop=True)
    if out.empty:
        raise ValueError("No usable rows after dropping empty and repeated coordinates.")
    return out.head(limit) if limit else out


def run(df, model, extract, progress=print, max_failures=4):
    """Forecast each site. Stops early after several map failures in a row."""
    from demandrange.forecast import forecast_site
    from demandrange.geo.osm import MapServiceError
    rows, fails, t0 = [], 0, time.time()
    for i, r in enumerate(df.itertuples(index=False), start=1):
        try:
            site, q = extract(float(r.lat), float(r.lon))
            fails = 0
        except MapServiceError as exc:
            fails += 1
            rows.append({"name": r.name, "status": "map lookup failed", "note": str(exc)[:80]})
            progress(f"[{i}/{len(df)}] {r.name}: map lookup failed")
            if fails >= max_failures:
                progress(f"Stopping: {max_failures} map lookups failed in a row. The free map servers look busy or blocked. "
                         "Wait a few minutes and re-run (finished sites are cached).")
                break
            continue
        site["market_within_5km"] = int(site["market_within_5km"])
        a = forecast_site(model, site, name=str(r.name))["years_avg"]
        rows.append({"name": r.name, "lat": r.lat, "lon": r.lon, "status": "ok",
                     "p10": round(a["p10"], 1), "p50": round(a["p50"], 1), "p90": round(a["p90"], 1),
                     "buildings_mapped": q["raw_counts"]["buildings"], "in_5_to_35_band": 5 <= a["p50"] <= 35})
        progress(f"[{i}/{len(df)}] {r.name}: {a['p50']:.1f} kWh middle case ({time.time() - t0:.0f}s elapsed)")
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--spend", type=float, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    try:
        import requests  # noqa: F401
    except ImportError:
        sys.exit("A package is missing. Activate your environment, then run:  pip install -r requirements.txt")
    from demandrange.config import REPORT_DIR
    from demandrange.geo import osm
    from demandrange.geo.features import features_from_coordinates
    from demandrange.service import get_model

    try:
        df = load_sites(args.input, args.limit)
    except (FileNotFoundError, ValueError) as exc:
        sys.exit(f"Problem with your input file: {exc}")
    print(f"Loaded {len(df)} unique sites from {args.input}.", flush=True)

    ok, info = osm.reachable()
    if not ok and not args.force:
        sys.exit(f"The free map service (OpenStreetMap Overpass) is not reachable: {info}\n"
                 "Check your internet, wait a few minutes, or re-run with --force to try anyway.")
    print("Map service reachable. Loading the model...", flush=True)
    res = run(df, get_model(), lambda la, lo: features_from_coordinates(la, lo, args.spend),
              progress=lambda m: print(m, flush=True))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(REPORT_DIR / "sanity_check_known_sites.csv", index=False)
    good = res[res["status"] == "ok"] if len(res) else res
    print(f"\n{len(good)} of {len(df)} sites forecast.")
    if len(good):
        print(f"{int(good['in_5_to_35_band'].sum())} of {len(good)} middle-case forecasts fall inside the 5 to 35 kWh band.")
    print("Saved reports/sanity_check_known_sites.csv")


if __name__ == "__main__":
    main()
