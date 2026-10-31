"""Data: a simulated training set (for the POC) and a loader for real data.

IMPORTANT, in plain words
-------------------------
The simulated data below is NOT real metered data. It is built from ranges
published in the brief (5-35 kWh per customer per month, current energy spend
of $5-20 per month, faster growth where businesses exist). It lets the whole
pipeline run end to end in 48 hours. When you get real data (partner meters or
World Bank Multi-Tier Framework surveys), save it as a CSV with the same
columns and run the pipeline again. Say this clearly in your disclosure
statement and your pitch.
"""
import numpy as np
import pandas as pd

from .config import (FEATURES, MODEL_COLUMNS, REQUIRED_COLUMNS, SEED, TARGET,
                     TIME_FEATURE, YEARS)

REGIONS = ["region_A", "region_B", "region_C", "region_D", "region_E", "region_F"]


def make_sites(n_sites=400, seed=SEED):
    """One row per village: what we could know before building anything."""
    rng = np.random.default_rng(seed)
    households = np.clip(rng.lognormal(np.log(400), 0.6, n_sites), 60, 2500)
    business = np.clip(rng.gamma(2.0, 4.5, n_sites) + households / 400, 0, 40)
    night_light = np.clip(
        rng.lognormal(-0.8, 0.7, n_sites) + 0.0006 * households + 0.02 * business,
        0, 3)
    dist = rng.uniform(3, 70, n_sites)
    p_market = np.clip(0.1 + households / 2000, 0, 0.9)
    market = (rng.random(n_sites) < p_market).astype(int)
    schools = np.clip(rng.poisson(households / 450), 0, 6)
    spend = np.clip(rng.uniform(5, 16, n_sites) + 1.5 * night_light, 5, 20)
    region = rng.choice(REGIONS, n_sites)
    return pd.DataFrame({
        "site_id": [f"site_{i:04d}" for i in range(n_sites)],
        "region": region,
        "households": households.round(0),
        "business_per_100": business.round(1),
        "night_light": night_light.round(2),
        "dist_to_grid_km": dist.round(1),
        "market_within_5km": market,
        "schools_clinics": schools,
        "energy_spend_usd": spend.round(1),
    })


def simulate_demand(sites, seed=SEED):
    """Turn villages into yearly demand rows (the 'metered' history).

    Assumptions (all editable, all disclosed):
    - Demand rises with spending, businesses, a market, schools/clinics, light.
    - Each region has a hidden offset, each site has hidden noise the model
      cannot see. This keeps the problem honest: some error is unavoidable.
    - Demand grows after connection, faster where businesses exist.
    """
    rng = np.random.default_rng(seed + 1)
    region_offset = {r: rng.normal(0, 0.12) for r in REGIONS}
    rows = []
    for _, s in sites.iterrows():
        base = (2.0 + 0.55 * s.energy_spend_usd + 0.22 * s.business_per_100
                + 2.5 * s.market_within_5km + 0.9 * s.schools_clinics
                + 1.8 * s.night_light)
        base *= np.exp(region_offset[s.region] + rng.normal(0, 0.15))
        growth = max(0.05, 0.20 + 0.012 * s.business_per_100 + rng.normal(0, 0.05))
        for t in YEARS:
            mult = 1 + growth * (1 - np.exp(-t / 1.5))
            kwh = base * mult * np.exp(rng.normal(0, 0.05))
            row = s.to_dict()
            row[TIME_FEATURE] = t
            row[TARGET] = float(np.clip(kwh, 3, 40))
            rows.append(row)
    out = pd.DataFrame(rows)
    out[TARGET] = out[TARGET].round(2)
    return out


def make_sample_dataset(n_sites=400, seed=SEED):
    return simulate_demand(make_sites(n_sites, seed), seed)


def load_sites_csv(path):
    """Load a real or simulated CSV and check it has what the model needs."""
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Your CSV is missing these columns: {missing}. "
            f"Expected columns: {REQUIRED_COLUMNS}")
    df = df.dropna(subset=MODEL_COLUMNS + [TARGET]).copy()
    if df.empty:
        raise ValueError("No usable rows after dropping empty values.")
    if (df[TARGET] <= 0).any():
        raise ValueError(f"'{TARGET}' must be greater than zero in every row.")
    return df
