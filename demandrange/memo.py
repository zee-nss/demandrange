"""Builds the one-page lender memo (plain language, no jargon)."""
from datetime import date


def build_memo(name, site, curve, years_avg, prod, fin, assumptions, drivers, notes=None, sizing=None):
    """curve: DataFrame with years and p10/p50/p90. drivers: sensitivity table."""
    prob = fin["prob_cover_debt"] * 100
    verdict = ("looks comfortable" if prob >= 80
               else "is uncertain" if prob >= 50 else "looks risky")
    lines = [
        f"# Demand forecast memo: {name}",
        f"*Prepared {date.today().isoformat()} with DemandRange (prototype, simulated training data).*",
        "",
        "## The short answer",
        f"In its first three years, each customer is likely to use about **{years_avg['p50']:.1f} kWh per month** "
        f"(low case {years_avg['p10']:.1f}, high case {years_avg['p90']:.1f}). "
        f"To cover its loan with a {assumptions.target_dscr:.1f}x safety margin, this site needs "
        f"**{fin['breakeven_kwh']:.1f} kWh per customer per month**. "
        f"We estimate a **{prob:.0f}% chance** it gets there, so the loan {verdict}.",
        "",
        "## How demand is expected to grow",
        "| Year after connection | Low case | Middle case | High case |",
        "|---|---|---|---|",
    ]
    for _, r in curve.iterrows():
        lines.append(f"| {int(r['year'])} | {r['p10']:.1f} | {r['p50']:.1f} | {r['p90']:.1f} |")
    lines += [
        "",
        "## What drives the estimate",
        "Change in the middle case (kWh per customer per month) if one input changes:",
    ]
    for _, r in drivers.head(4).iterrows():
        lines.append(f"- {r['what_changes']}: {r['change_kwh']:+.2f}")
    lines += [
        "",
        "## Business customers and the cost of power",
        f"Estimated load factor: **{prod['load_factor']*100:.0f}%**. "
        f"That makes each kWh about **{prod['cost_saving_vs_household_only_pct']:.0f}% cheaper** "
        "than a households-only system (calibrated to the ESMAP figures in the brief).",
        "Daytime customers worth signing first: " + "; ".join(prod["anchors"]) + ".",
        "",
        "## Can customers afford it?",
        f"At a tariff of ${assumptions.tariff_usd_per_kwh:.2f} per kWh, the typical monthly bill is "
        f"**${fin['typical_monthly_bill_usd']:.2f}**, which is "
        f"**{fin['bill_vs_current_spend']*100:.0f}%** of what households spend on candles, kerosene, "
        "batteries and diesel today.",
        "",
        "## Assumptions (replace the placeholders before sharing)",
        f"- {assumptions.customers} customers; ${assumptions.capex_per_customer_usd:.0f} build cost per customer (placeholder)",
        f"- ${assumptions.opex_per_customer_year_usd:.0f} running cost per customer per year (placeholder)",
        f"- {assumptions.debt_share*100:.0f}% debt at {assumptions.interest_rate*100:.0f}% over {assumptions.tenor_years} years",
        f"- Annual loan payments: ${fin['annual_debt_service_usd']:,.0f}",
        "",
        *( sizing_lines(sizing) if sizing else [] ),
        "## Where the inputs came from",
        *( [f"- {n}" for n in notes] if notes else ["- Entered by hand."] ),
        "",
        "## Honest limits",
        "This prototype was trained on simulated villages built from ranges in the problem brief. "
        "Its numbers show how the method works, not what any real site will do. "
        "Validate with real metered data before using it for a financing decision.",
    ]
    return "\n".join(lines)


def sizing_lines(z):
    s, sol, c = z["sizes"], z["solar"], z["cost_of_wrong"]
    return [
        "## What system the forecast implies",
        f"Sunshine here averages {sol['annual_kwh_m2_day']} kWh per m2 per day, and {sol['worst_month_kwh_m2_day']} in the poorest month ({sol['worst_month'].title()}), from NASA POWER. "
        "Designing for the poorest month, the solar array and battery would be:",
        f"- Low case: about {s['low_case']['pv_kwp']:.0f} kW of solar and {s['low_case']['battery_kwh']:.0f} kWh of battery",
        f"- Middle case: about {s['middle_case']['pv_kwp']:.0f} kW of solar and {s['middle_case']['battery_kwh']:.0f} kWh of battery",
        f"- High case: about {s['high_case']['pv_kwp']:.0f} kW of solar and {s['high_case']['battery_kwh']:.0f} kWh of battery",
        f"Cost of being wrong (using about USD {c['capex_per_person_usd']:.0f} per person from the ESMAP figures): each 10% sizing error on this site is about "
        f"USD {c['capex_per_10pct_sizing_error_usd']:,.0f}. Building for the high case when the middle case happens leaves about USD {c['wasted_if_sized_for_high_case_usd']:,.0f} of capacity unused.",
        "",
    ]
