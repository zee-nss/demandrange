"""Run this once. It does everything: data, validation, training, sample memo.

    python run_pipeline.py                      # use simulated data
    python run_pipeline.py --data data/real.csv # use your own CSV
"""
import argparse

from demandrange.config import (MODEL_PATH, REPORT_DIR, SAMPLE_DATA_PATH)
from demandrange.data import load_sites_csv, make_sample_dataset
from demandrange.forecast import forecast_site
from demandrange.model import DemandRangeModel
from demandrange.validate import run_validation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="Path to your own CSV (optional)")
    args = parser.parse_args()

    if args.data:
        print(f"Loading your data from {args.data} ...")
        df = load_sites_csv(args.data)
    else:
        print("Creating simulated sample data ...")
        df = make_sample_dataset()
        SAMPLE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(SAMPLE_DATA_PATH, index=False)
        print(f"  saved {len(df)} rows to {SAMPLE_DATA_PATH}")

    print("Validating on villages the model has never seen ...")
    result = run_validation(df)
    s, r = result["held_out_sites"], result["held_out_regions"]
    print(f"  Held-out sites : error {s['mae_kwh']} kWh "
          f"({s['improvement_vs_baseline_pct']}% better than the average-guess baseline), "
          f"range covers {s['range_coverage_pct']}% of actuals")
    if "mae_kwh" in r:
        print(f"  Held-out region: error {r['mae_kwh']} kWh "
              f"({r['improvement_vs_baseline_pct']}% better than baseline)")
    else:
        print(f"  Held-out region: {r['note']}")

    print("Training the final model on all data ...")
    model = DemandRangeModel().fit(df)
    model.meta["data_source"] = args.data if args.data else "simulated"
    model.save(MODEL_PATH)

    print("Writing a sample lender memo ...")
    site = {"households": 450, "business_per_100": 14, "night_light": 0.7,
            "dist_to_grid_km": 30, "market_within_5km": 1, "schools_clinics": 2,
            "energy_spend_usd": 11}
    out = forecast_site(model, site, name="Sample village")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "sample_lender_memo.md").write_text(out["memo"])
    print("Done. Start the app with:  streamlit run app.py")


if __name__ == "__main__":
    main()
