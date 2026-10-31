"""Turn an operator's meter data into a training table, using real coordinates.

    python scripts/build_training_table.py --input data/raw/operator_sites.csv

Accepted layouts (the script detects which one you have):

A) One row per site per year since connection
   site_id, lat, lon, years_since_connection, kwh_per_customer_month
   (optional: region, energy_spend_usd)

B) One row per site per month
   site_id, lat, lon, connection_date, month, kwh_total, customers
   (or kwh_per_customer_month instead of kwh_total + customers)
   (optional: region, energy_spend_usd)

For each site, village features are read from the map using the coordinates
(same code the live app uses, so training and prediction match).
Sites the map services could not read are saved to the *_skipped.csv file.
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demandrange.config import DATA_DIR, FEATURES, REQUIRED_COLUMNS, TARGET, TIME_FEATURE
from demandrange.geo.features import features_from_coordinates
from demandrange.geo.osm import MapServiceError


def to_site_years(df):
    """Bring layout A or B to one row per site per year since connection."""
    need = {"site_id", "lat", "lon"}
    if not need.issubset(df.columns):
        raise ValueError(f"Your file needs the columns {sorted(need)}.")
    if {TIME_FEATURE, TARGET}.issubset(df.columns):
        out = df.copy()
    elif {"month", "connection_date"}.issubset(df.columns):
        out = df.copy()
        if TARGET not in out.columns:
            if not {"kwh_total", "customers"}.issubset(out.columns):
                raise ValueError("Monthly layout needs kwh_per_customer_month, or kwh_total and customers.")
            out[TARGET] = out["kwh_total"] / out["customers"]
        months = (pd.to_datetime(out["month"]) - pd.to_datetime(out["connection_date"])).dt.days / 30.44
        out[TIME_FEATURE] = (months // 12).clip(lower=0).astype(int)
        keep = [c for c in ["site_id", "lat", "lon", "region", "energy_spend_usd"] if c in out.columns]
        out = (out.groupby(keep + [TIME_FEATURE], dropna=False)[TARGET].mean().reset_index())
    else:
        raise ValueError("Could not tell your layout. See the top of this script for the two accepted layouts.")
    out = out.dropna(subset=[TARGET])
    out = out[out[TARGET] > 0]
    if "region" not in out.columns:
        out["region"] = "region_1"
    return out


def build_table(df, extract, delay=0.0):
    """Returns (training_table, skipped_sites). `extract(lat, lon, spend)` is injectable for tests."""
    rows = to_site_years(df)
    sites = rows.drop_duplicates("site_id")
    feats, skipped = {}, []
    for _, s in sites.iterrows():
        spend = s["energy_spend_usd"] if "energy_spend_usd" in sites.columns and pd.notna(s.get("energy_spend_usd")) else None
        try:
            f, _ = extract(float(s["lat"]), float(s["lon"]), spend)
            feats[s["site_id"]] = f
        except MapServiceError as exc:
            skipped.append({"site_id": s["site_id"], "reason": str(exc)})
        time.sleep(delay)
    table = rows[rows["site_id"].isin(feats)].copy()
    for f in FEATURES:
        table[f] = table["site_id"].map(lambda sid, f=f: feats[sid][f])
    table = table[REQUIRED_COLUMNS]
    return table.reset_index(drop=True), pd.DataFrame(skipped, columns=["site_id", "reason"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", default=str(DATA_DIR / "real_training.csv"))
    ap.add_argument("--nightlight-tif", default=None, help="optional WorldPop night-light GeoTIFF")
    args = ap.parse_args()

    df = pd.read_csv(args.input)
    extract = lambda la, lo, sp: features_from_coordinates(la, lo, sp, args.nightlight_tif)
    table, skipped = build_table(df, extract, delay=1.0)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    if len(skipped):
        skipped.to_csv(out.with_name(out.stem + "_skipped.csv"), index=False)
    print(f"Wrote {len(table)} rows for {table['site_id'].nunique()} sites to {out}")
    if len(skipped):
        print(f"  {len(skipped)} site(s) skipped, see {out.stem}_skipped.csv")
    print("Next:  python run_pipeline.py --data " + str(out))


if __name__ == "__main__":
    main()
