"""Will the forecast cover the loan? A lender's question, answered simply.

All money inputs below are PLACEHOLDERS so the tool runs. Replace them with
real numbers (ESMAP and AMDA publish mini-grid cost benchmarks) before using
the output with anyone.
"""
from dataclasses import dataclass
from math import erf, log, sqrt


@dataclass
class Assumptions:
    customers: int = 400
    capex_per_customer_usd: float = 600.0     # PLACEHOLDER
    opex_per_customer_year_usd: float = 25.0  # PLACEHOLDER
    tariff_usd_per_kwh: float = 0.45          # PLACEHOLDER
    debt_share: float = 0.7
    interest_rate: float = 0.10
    tenor_years: int = 10
    target_dscr: float = 1.2  # lenders usually want income comfortably above debt payments


def annual_debt_service(a):
    debt = a.customers * a.capex_per_customer_usd * a.debt_share
    r, n = a.interest_rate, a.tenor_years
    return debt * r / (1 - (1 + r) ** -n)


def breakeven_kwh(a):
    """Demand (kWh per customer per month) needed to meet the target DSCR."""
    revenue_needed = (a.target_dscr * annual_debt_service(a)
                      + a.customers * a.opex_per_customer_year_usd)
    return revenue_needed / (a.customers * a.tariff_usd_per_kwh * 12)


def _normal_cdf(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def prob_demand_above(p10, p50, p90, threshold):
    """Chance demand is at least `threshold`, using the forecast range.

    We fit a bell curve on a log scale through the low (P10) and high (P90)
    cases. P10 and P90 are 2.563 standard deviations apart.
    """
    sigma = max((log(p90) - log(p10)) / 2.563, 1e-6)
    z = (log(threshold) - log(p50)) / sigma
    return 1 - _normal_cdf(z)


def how_wrong_can_it_be(p50, breakeven):
    """How far demand can fall below the middle case before the loan is in trouble."""
    return max(0.0, (1 - breakeven / p50) * 100)


def monthly_bill_usd(kwh, tariff):
    return kwh * tariff


def finance_summary(forecast_years_1_to_3, a, current_spend_usd):
    """forecast_years_1_to_3: dict with averaged p10, p50, p90."""
    p10, p50, p90 = (forecast_years_1_to_3[k] for k in ("p10", "p50", "p90"))
    be = breakeven_kwh(a)
    bill = monthly_bill_usd(p50, a.tariff_usd_per_kwh)
    return {
        "breakeven_kwh": be,
        "prob_cover_debt": prob_demand_above(p10, p50, p90, be),
        "cushion_pct": how_wrong_can_it_be(p50, be),
        "annual_debt_service_usd": annual_debt_service(a),
        "typical_monthly_bill_usd": bill,
        "bill_vs_current_spend": bill / current_spend_usd,
    }
