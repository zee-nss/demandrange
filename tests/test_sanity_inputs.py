"""The sanity-check script: file handling, clear errors, early stop, GeoJSON conversion."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import geojson_to_csv as g2c  # noqa: E402
import sanity_check_known_sites as san  # noqa: E402
from demandrange.geo import osm  # noqa: E402


def test_load_sites_aliases_dupes_and_limit(tmp_path):
    f = tmp_path / "s.csv"
    pd.DataFrame({"Village": ["a", "b", "c", "d"], "Latitude": [1, 2, 2, "x"], "Longitude": [3, 4, 4, 5]}).to_csv(f, index=False)
    df = san.load_sites(f)
    assert list(df.columns) == ["name", "lat", "lon"] and len(df) == 2        # repeated and bad rows dropped
    assert len(san.load_sites(f, limit=1)) == 1


def test_missing_file_and_missing_columns_are_explained(tmp_path):
    (tmp_path / "other.csv").write_text("a,b\n1,2\n")
    with pytest.raises(FileNotFoundError, match="other.csv"):
        san.load_sites(tmp_path / "nope.csv")
    with pytest.raises(ValueError, match="No 'lat' column"):
        san.load_sites(tmp_path / "other.csv")


def test_run_stops_after_repeated_map_failures():
    df = pd.DataFrame({"name": list("abcdefg"), "lat": range(7), "lon": range(7)})
    calls, msgs = [], []

    def boom(la, lo):
        calls.append(1)
        raise osm.MapServiceError("down")
    out = san.run(df, None, boom, progress=msgs.append, max_failures=3)
    assert len(calls) == 3 and any("Stopping" in m for m in msgs) and (out["status"] == "map lookup failed").all()


def test_geojson_points_swap_to_lat_lon_and_lines_are_rejected():
    geo = {"features": [{"geometry": {"type": "Point", "coordinates": [42.5, -0.36]}, "properties": {"n": "Kismayo"}}]}
    row = g2c.convert(geo, name_field="n").iloc[0]
    assert (row["lat"], row["lon"], row["name"]) == (-0.36, 42.5, "Kismayo")
    with pytest.raises(ValueError, match="not a Point"):
        g2c.convert({"features": [{"geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]}}]})
