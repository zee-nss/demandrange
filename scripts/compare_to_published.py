"""Compare DemandRange forecasts with REAL published meter averages (free, no purchase).

    python scripts/compare_to_published.py
    python scripts/compare_to_published.py --benchmarks data/benchmarks/drc_published_means.csv

The benchmark file holds average monthly kWh per household and per small business
in three real areas of North Kivu, DRC (Lunanga et al. 2026). For each area the
script finds the place on the map, forecasts it, and shows how the published
average compares with your low to high range.

How to say it honestly: this is a comparison with published averages from three
areas of ONE operator, not a full validation. A model trained on simulated data
may sit far from these numbers. If it does, that is a result: say so, and use it
to explain why real training data matters.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demandrange.config import REPORT_DIR
from demandrange.forecast import forecast_site
from demandrange.geo import osm
from demandrange.geo.features import features_from_coordinates
from demandrange.service import get_model


def run(bench, model, geocode, extract, country="Democratic Republic of the Congo"):
    rows = []
    for area in bench["area"].unique():
        try:
            place = geocode(f"{area}, {country}")[0]
            site, q = extract(place["lat"], place["lon"])
        except (osm.MapServiceError, IndexError) as exc:
            rows.append({"area": area, "status": f"lookup failed: {str(exc)[:60]}"})
            continue
        site["market_within_5km"] = int(site["market_within_5km"])
        avg = forecast_site(model, site, name=area)["years_avg"]
        hh = bench[(bench.area == area) & (bench.customer_type == "household")].iloc[0]
        sme = bench[(bench.area == area) & (bench.customer_type == "SME")].iloc[0]
        rows.append({"area": area, "status": "ok", "buildings_mapped": q["raw_counts"]["buildings"],
                     "forecast_p10": round(avg["p10"], 1), "forecast_p50": round(avg["p50"], 1),
                     "forecast_p90": round(avg["p90"], 1),
                     "published_household_mean": hh.mean_kwh_per_month, "published_household_median": hh.median_kwh_per_month,
                     "household_mean_inside_range": avg["p10"] <= hh.mean_kwh_per_month <= avg["p90"],
                     "published_sme_mean": sme.mean_kwh_per_month})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmarks", default="data/benchmarks/drc_published_means.csv")
    args = ap.parse_args()
    res = run(pd.read_csv(args.benchmarks), get_model(), osm.geocode,
              lambda la, lo: features_from_coordinates(la, lo, None))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(REPORT_DIR / "compare_to_published.csv", index=False)
    print(res.to_string(index=False))
    print("Saved reports/compare_to_published.csv")


if __name__ == "__main__":
    main()
