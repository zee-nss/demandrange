"""One call that turns a village description into a full forecast."""
import math

import pandas as pd

from .config import TIME_FEATURE, YEARS
from .explain import sensitivity
from .finance import Assumptions, finance_summary
from .memo import build_memo
from .productive_use import productive_use_summary
from .sizing import SizingAssumptions, cost_of_being_wrong, sizing_range


def growth_curve(model, site, years=YEARS):
    rows = pd.DataFrame([{**site, TIME_FEATURE: t} for t in years])
    pred = model.predict(rows)
    pred.insert(0, "year", list(years))
    return pred.reset_index(drop=True)


DEFAULT_SPEND_USD = 10.0  # used only for the affordability comparison when spend is unknown


def forecast_site(model, site, name="Example village", assumptions=None, notes=None, solar=None):
    """Returns everything the app and the memo need."""
    assumptions = assumptions or Assumptions()
    curve = growth_curve(model, site)
    first3 = curve[curve["year"].between(1, 3)]
    years_avg = {k: float(first3[k].mean()) for k in ("p10", "p50", "p90")}
    prod = productive_use_summary(site["business_per_100"],
                                  site["market_within_5km"], site["schools_clinics"])
    spend = site.get("energy_spend_usd")
    notes = list(notes or [])
    if spend is None or (isinstance(spend, float) and math.isnan(spend)):
        spend = DEFAULT_SPEND_USD
        notes.append(f"Current household energy spend was unknown. The affordability check assumes ${spend:.0f} per month.")
    fin = finance_summary(years_avg, assumptions, spend)
    drivers = sensitivity(model, site)
    sizing = None
    if solar:
        sa = SizingAssumptions(customers=assumptions.customers)
        sizing = {"solar": solar, "sizes": sizing_range(years_avg, solar["worst_month_kwh_m2_day"], sa),
                  "cost_of_wrong": cost_of_being_wrong(years_avg, sa)}
    memo = build_memo(name, site, curve, years_avg, prod, fin, assumptions, drivers, notes, sizing)
    return {"sizing": sizing, "curve": curve, "years_avg": years_avg, "productive_use": prod,
            "finance": fin, "drivers": drivers, "memo": memo}
