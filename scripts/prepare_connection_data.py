"""Turn connection-level meter records (like a research dataset of one operator's
customers) into the site-level file that build_training_table.py reads.

    python scripts/prepare_connection_data.py --input data/raw/connections.csv

Your file needs ONE ROW PER CONNECTION PER MONTH with at least:
  a locality (village or town) name, a connection id, a month, and kWh used.
Column names differ between datasets, so tell the script yours:

    --locality-col  --connection-col  --month-col  --kwh-col
    --type-col      (optional: household or business/SME)
    --lat-col --lon-col   (optional: GPS of each connection)
    --centroids FILE      (optional: CSV with locality,lat,lon, if there is no GPS)
    --cell-km 1.0         (optional, needs GPS: split each locality into 1 km cells
                           and treat every cell as its own site. Gives many more
                           real sites to validate on than a handful of localities.)

If a column name is wrong, the script prints the columns it found.
It also prints the average kWh per connection by year since commissioning, and
how much more a business uses than a household. Those are real-data facts you
can put straight on a slide.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def prepare(df, locality, connection, month, kwh, type_col=None, lat=None, lon=None,
            centroids=None, cell_km=None, min_connections=10):
    for name, col in [("locality", locality), ("connection", connection), ("month", month), ("kwh", kwh)]:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' (for --{name}-col) not found. Columns in your file: {list(df.columns)}")
    d = df.copy()
    d["_month"] = pd.to_datetime(d[month], errors="coerce")
    d["_kwh"] = pd.to_numeric(d[kwh], errors="coerce")
    d = d.dropna(subset=["_month", "_kwh"])
    d = d[d["_kwh"] >= 0]
    d["_month"] = d["_month"].dt.to_period("M").dt.to_timestamp()

    # Where is each connection? GPS if given, else the locality centre.
    if lat and lon and lat in d.columns and lon in d.columns:
        d["_lat"], d["_lon"] = pd.to_numeric(d[lat], errors="coerce"), pd.to_numeric(d[lon], errors="coerce")
    elif centroids is not None:
        c = centroids.rename(columns={"locality": locality}).set_index(locality)[["lat", "lon"]]
        d = d.join(c, on=locality).rename(columns={"lat": "_lat", "lon": "_lon"})
    else:
        raise ValueError("Need coordinates: give --lat-col and --lon-col, or --centroids with locality,lat,lon.")
    d = d.dropna(subset=["_lat", "_lon"])
    if d.empty:
        raise ValueError("No rows with usable coordinates.")

    # A "site" is a whole locality, or a grid cell inside it.
    if cell_km:
        if not (lat and lon):
            raise ValueError("--cell-km needs GPS columns (--lat-col and --lon-col).")
        dlat = cell_km / 110.57
        dlon = cell_km / (111.32 * np.cos(np.radians(d["_lat"].mean())))
        d["_site"] = (d[locality].astype(str) + "_" + (d["_lat"] // dlat).astype(int).astype(str)
                      + "_" + (d["_lon"] // dlon).astype(int).astype(str))
        per_site = d.groupby("_site")[connection].nunique()
        d = d[d["_site"].isin(per_site[per_site >= min_connections].index)]
        if d.empty:
            raise ValueError(f"No cell has {min_connections}+ connections. Try a bigger --cell-km.")
    else:
        d["_site"] = d[locality].astype(str)

    commissioned = d.groupby("_site")["_month"].min().rename("connection_date")
    agg = (d.groupby(["_site", "_month"])
             .agg(kwh_total=("_kwh", "sum"), customers=(connection, "nunique"),
                  lat=("_lat", "mean"), lon=("_lon", "mean"), region=(locality, "first"))
             .reset_index().rename(columns={"_site": "site_id", "_month": "month"}))
    agg = agg.join(commissioned, on="site_id")
    # Fix each site's location to one point (its mean).
    pos = agg.groupby("site_id")[["lat", "lon"]].transform("mean")
    agg["lat"], agg["lon"] = pos["lat"], pos["lon"]
    out = agg[["site_id", "region", "lat", "lon", "connection_date", "month", "kwh_total", "customers"]]

    facts = {}
    months = ((agg["month"] - agg["connection_date"]).dt.days / 30.44 // 12).clip(lower=0).astype(int)
    per = (agg.assign(year=months, per_cust=agg["kwh_total"] / agg["customers"])
              .groupby("year")["per_cust"].mean().round(2))
    facts["mean_kwh_per_connection_by_year"] = per.to_dict()
    if type_col and type_col in d.columns:
        t = d.groupby(d[type_col].astype(str))["_kwh"].mean()
        facts["mean_kwh_per_connection_month_by_type"] = t.round(2).to_dict()
    facts["sites"] = int(out["site_id"].nunique())
    facts["localities"] = int(out["region"].nunique())
    facts["months_span"] = f"{out['month'].min():%Y-%m} to {out['month'].max():%Y-%m}"
    return out, facts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default="data/raw/operator_sites.csv")
    ap.add_argument("--locality-col", default="locality")
    ap.add_argument("--connection-col", default="connection_id")
    ap.add_argument("--month-col", default="month")
    ap.add_argument("--kwh-col", default="kwh")
    ap.add_argument("--type-col")
    ap.add_argument("--lat-col")
    ap.add_argument("--lon-col")
    ap.add_argument("--centroids")
    ap.add_argument("--cell-km", type=float)
    ap.add_argument("--min-connections", type=int, default=10)
    a = ap.parse_args()
    df = pd.read_csv(a.input)
    cents = pd.read_csv(a.centroids) if a.centroids else None
    out, facts = prepare(df, a.locality_col, a.connection_col, a.month_col, a.kwh_col, a.type_col,
                         a.lat_col, a.lon_col, cents, a.cell_km, a.min_connections)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.output, index=False)
    print(f"Wrote {len(out)} site-months for {facts['sites']} sites in {facts['localities']} localities "
          f"({facts['months_span']}) to {a.output}")
    print("Average kWh per connection per month, by year since commissioning:", facts["mean_kwh_per_connection_by_year"])
    if "mean_kwh_per_connection_month_by_type" in facts:
        print("By customer type:", facts["mean_kwh_per_connection_month_by_type"])
    print("Next:  python scripts/build_training_table.py --input " + a.output)


if __name__ == "__main__":
    main()
