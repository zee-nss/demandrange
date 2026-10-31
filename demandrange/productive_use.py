"""Productive use: daytime businesses that raise the load factor.

The brief (citing ESMAP) says a household-only mini-grid runs at about a 22%
load factor, and adding daytime business use to reach 40% cut the cost of
power by 25%. We use those two points to calibrate a simple curve:

    cost_index(load_factor) = A + B / load_factor      (index = 1.0 at 22%)

Solving for the two published points gives A = 0.4444 and B = 0.1222.
This is a teaching-grade estimate, not an engineering model.
"""
LF_HOUSEHOLD_ONLY = 0.22
LF_WITH_BUSINESS = 0.40
_B = (1.0 - 0.75) / (1 / LF_HOUSEHOLD_ONLY - 1 / LF_WITH_BUSINESS)
_A = 1.0 - _B / LF_HOUSEHOLD_ONLY


def cost_index(load_factor):
    """Relative cost of each kWh. 1.00 = household-only (22%) mini-grid."""
    return _A + _B / load_factor


def estimate_load_factor(business_per_100, market_within_5km):
    """Rough load factor from how much business activity the village has.

    Scales from 22% (no business) up to 40% (about 25 businesses per 100
    homes, or fewer with a nearby market). Capped at 40% because that is the
    highest point the brief gives evidence for.
    """
    activity = business_per_100 + (5 if market_within_5km else 0)
    share = min(1.0, activity / 25.0)
    return LF_HOUSEHOLD_ONLY + (LF_WITH_BUSINESS - LF_HOUSEHOLD_ONLY) * share


def anchor_checklist(business_per_100, market_within_5km, schools_clinics):
    """Daytime customers worth signing up first. Confirm with the community."""
    ideas = []
    if market_within_5km:
        ideas += ["Cold storage for market sellers", "Grain milling or processing"]
    if schools_clinics:
        ideas += ["Clinic vaccine fridge and school lighting (steady daytime load)"]
    if business_per_100 >= 10:
        ideas += ["Welding and carpentry workshops", "Barbers, salons and phone charging"]
    if not ideas:
        ideas = ["Water pumping", "Small grain mill",
                 "Survey the village for any daytime business before sizing the system"]
    return ideas


def productive_use_summary(business_per_100, market_within_5km, schools_clinics):
    lf = estimate_load_factor(business_per_100, market_within_5km)
    return {
        "load_factor": lf,
        "cost_index": cost_index(lf),
        "cost_saving_vs_household_only_pct": (1 - cost_index(lf)) * 100,
        "anchors": anchor_checklist(business_per_100, market_within_5km, schools_clinics),
    }
