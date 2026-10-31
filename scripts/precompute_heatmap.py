"""Build a big heatmap ahead of time so the demo loads instantly.

    python scripts/precompute_heatmap.py --name kaduna --lat 10.52 --lon 7.44 \
        --half-width-km 15 --cells 6

Saves data/heatmaps/<name>.geojson and .csv. Run it at home on good internet,
then commit the files (or upload them to your deployed API).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demandrange.config import DATA_DIR
from demandrange.geo.grid import build_heatmap, heatmap_to_csv
from demandrange.service import get_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--half-width-km", type=float, default=15)
    ap.add_argument("--cells", type=int, default=6)
    ap.add_argument("--metric", default="p50", choices=["p10", "p50", "p90", "prob_cover_debt"])
    ap.add_argument("--spend", type=float, default=None, help="monthly household energy spend, USD")
    args = ap.parse_args()
    fc = build_heatmap(get_model(), args.lat, args.lon, args.half_width_km, args.cells,
                       year=None, metric=args.metric, energy_spend_usd=args.spend)
    out = DATA_DIR / "heatmaps"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.name}.geojson").write_text(json.dumps(fc))
    (out / f"{args.name}.csv").write_text(heatmap_to_csv(fc))
    m = fc["metadata"]
    print(f"Saved {m['cells_ok']} cells ({m['cells_failed']} failed) to {out}/{args.name}.geojson")


if __name__ == "__main__":
    main()
