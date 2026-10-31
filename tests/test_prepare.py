"""Connection-level data -> site-level file (no internet, no real data needed)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_training_table as btt  # noqa: E402
import prepare_connection_data as pcd  # noqa: E402


def fake_connections(n_per_loc=40, months=30):
    rng = np.random.default_rng(1)
    rows = []
    for loc, (la, lo) in {"A": (-1.0, 29.0), "B": (-1.1, 29.2), "C": (-1.2, 29.4)}.items():
        for c in range(n_per_loc):
            clat, clon = la + rng.normal(0, 0.01), lo + rng.normal(0, 0.01)
            kind = "business" if c % 8 == 0 else "household"
            for m in range(months):
                rows.append({"loc": loc, "cid": f"{loc}{c}", "ym": f"{2020 + m // 12}-{m % 12 + 1:02d}-01",
                             "use": (30 if kind == "business" else 6) * (1 + m / 40) + rng.normal(0, 1),
                             "kind": kind, "la": clat, "lo": clon})
    return pd.DataFrame(rows)


def test_locality_level_with_gps():
    out, facts = pcd.prepare(fake_connections(), "loc", "cid", "ym", "use", "kind", "la", "lo")
    assert facts["sites"] == 3 and set(out.columns) >= {"site_id", "lat", "lon", "month", "kwh_total", "customers"}
    by_year = facts["mean_kwh_per_connection_by_year"]
    assert by_year[max(by_year)] > by_year[0]                        # demand grows
    t = facts["mean_kwh_per_connection_month_by_type"]
    assert t["business"] > 3 * t["household"]                       # businesses use more


def test_cells_make_more_sites_and_feed_the_builder():
    out, facts = pcd.prepare(fake_connections(), "loc", "cid", "ym", "use", None, "la", "lo", cell_km=1.0, min_connections=3)
    assert facts["sites"] > 3 and facts["localities"] == 3
    extract = lambda la, lo, sp: (dict(households=300.0, business_per_100=10.0, night_light=float("nan"),
                                       dist_to_grid_km=20.0, market_within_5km=1, schools_clinics=1,
                                       energy_spend_usd=float("nan")), {})
    table, skipped = btt.build_table(out, extract)
    assert table["site_id"].nunique() == facts["sites"] and skipped.empty


def test_centroids_and_clear_errors():
    df = fake_connections().drop(columns=["la", "lo"])
    cents = pd.DataFrame({"locality": ["A", "B", "C"], "lat": [-1, -1.1, -1.2], "lon": [29, 29.2, 29.4]})
    out, _ = pcd.prepare(df, "loc", "cid", "ym", "use", centroids=cents)
    assert out["site_id"].nunique() == 3
    with pytest.raises(ValueError, match="Columns in your file"):
        pcd.prepare(df, "wrong", "cid", "ym", "use", centroids=cents)
    with pytest.raises(ValueError, match="Need coordinates"):
        pcd.prepare(df, "loc", "cid", "ym", "use")
