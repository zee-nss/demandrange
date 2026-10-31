"""Shared settings. Change things here, not in five different files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"

SAMPLE_DATA_PATH = DATA_DIR / "sample_sites.csv"
MODEL_PATH = MODEL_DIR / "demandrange.joblib"

SEED = 42

# What the model knows about a village (all can come from public data):
FEATURES = [
    "households",          # count of homes (from building footprints)
    "business_per_100",    # small businesses per 100 homes
    "night_light",         # night-time light brightness nearby (0 = dark)
    "dist_to_grid_km",     # distance to the nearest grid line
    "market_within_5km",   # 1 if a market is within 5 km, else 0
    "schools_clinics",     # number of schools and clinics nearby
    "energy_spend_usd",    # what a household spends per month on candles,
                           # kerosene, batteries, diesel today
]
TIME_FEATURE = "years_since_connection"
TARGET = "kwh_per_customer_month"
MODEL_COLUMNS = FEATURES + [TIME_FEATURE]

REQUIRED_COLUMNS = ["site_id", "region"] + MODEL_COLUMNS + [TARGET]

QUANTILES = (0.1, 0.5, 0.9)
YEARS = (0, 1, 2, 3, 4)

# Plain-language names, used in the app and the lender memo.
PLAIN = {
    "households": "number of households",
    "business_per_100": "businesses per 100 households",
    "night_light": "night-time light level",
    "dist_to_grid_km": "distance to the grid",
    "market_within_5km": "a market within 5 km",
    "schools_clinics": "schools and clinics nearby",
    "energy_spend_usd": "current monthly energy spending",
    "years_since_connection": "years since connection",
}

# Starting values and limits for the app sliders.
FEATURE_LIMITS = {
    "households": (50, 2500, 400),
    "business_per_100": (0.0, 40.0, 10.0),
    "night_light": (0.0, 3.0, 0.6),
    "dist_to_grid_km": (1.0, 80.0, 25.0),
    "schools_clinics": (0, 6, 1),
    "energy_spend_usd": (5.0, 20.0, 10.0),
}
