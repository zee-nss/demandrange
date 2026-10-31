"""From forecast to system size and the cost of getting it wrong (unit economics).

All physics here is simple on purpose: a solar array and battery big enough for
the forecast demand on the sunniest-poorest month. Costs use ONE sourced number,
the ESMAP benchmark quoted in Brief 03: about USD 127 billion to connect 490
million people, which is about USD 259 per person. Replace the assumptions below
with sourced local values before you rely on them.
"""
from dataclasses import dataclass

CAPEX_PER_PERSON_USD = 127e9 / 490e6   # about 259, from the ESMAP figures in Brief 03
DAYS_PER_MONTH = 30.4


@dataclass
class SizingAssumptions:
    customers: int = 400
    performance_ratio: float = 0.75      # real-world losses in a solar array (assumption)
    battery_autonomy_days: float = 1.0   # days of storage (assumption)
    depth_of_discharge: float = 0.8      # usable share of the battery (assumption)
    persons_per_customer: float = 5.0    # people served per connection (assumption)


def size_for_demand(kwh_per_customer_month, sun_hours, a):
    """Solar array (kWp) and battery (kWh) for one demand level."""
    daily_kwh = kwh_per_customer_month * a.customers / DAYS_PER_MONTH
    return {"daily_kwh": daily_kwh,
            "pv_kwp": daily_kwh / (sun_hours * a.performance_ratio),
            "battery_kwh": daily_kwh * a.battery_autonomy_days / a.depth_of_discharge}


def sizing_range(avg, sun_hours, a):
    """Low, middle and high case system sizes from the forecast range."""
    return {k: size_for_demand(avg[p], sun_hours, a) for k, p in
            (("low_case", "p10"), ("middle_case", "p50"), ("high_case", "p90"))}


def cost_of_being_wrong(avg, a):
    """What a wrong forecast costs, using the ESMAP cost per person.

    Sizing for the high case when the middle case happens wastes capital.
    Sizing for the middle case when the high case happens leaves a shortfall.
    """
    persons = a.customers * a.persons_per_customer
    capex = persons * CAPEX_PER_PERSON_USD
    over = max(0.0, 1 - avg["p50"] / avg["p90"])      # share of a high-case build that goes unused
    short = max(0.0, 1 - avg["p50"] / avg["p90"])     # share of high-case demand a middle build misses
    return {"persons_served": persons, "benchmark_capex_usd": capex,
            "capex_per_person_usd": CAPEX_PER_PERSON_USD,
            "wasted_if_sized_for_high_case_usd": capex * over,
            "share_of_demand_unmet_if_sized_for_middle_case": short,
            "capex_per_10pct_sizing_error_usd": capex * 0.10}
