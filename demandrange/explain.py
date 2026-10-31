"""Why this range? Change one input at a time and show what moves."""
import pandas as pd

from .config import FEATURES, PLAIN, TIME_FEATURE


def sensitivity(model, site, year=2, bump=0.20):
    """Raise each input by 20% (or flip the market switch) and show the change.

    site: dict of feature values. Returns a table sorted by size of effect.
    """
    base_row = {**site, TIME_FEATURE: year}
    base = model.predict(pd.DataFrame([base_row])).iloc[0]["p50"]
    rows = []
    for f in FEATURES:
        if pd.isna(base_row[f]):
            continue  # nothing to change if we do not know this input
        changed = dict(base_row)
        if f == "market_within_5km":
            changed[f] = 0 if base_row[f] else 1
            label = "Market nearby: " + ("remove it" if base_row[f] else "add it")
        elif f == "schools_clinics":
            changed[f] = base_row[f] + 1
            label = "One more school or clinic"
        else:
            changed[f] = base_row[f] * (1 + bump)
            label = f"{PLAIN[f].capitalize()} +20%"
        new = model.predict(pd.DataFrame([changed])).iloc[0]["p50"]
        rows.append({"what_changes": label, "change_kwh": new - base})
    out = pd.DataFrame(rows)
    out["abs"] = out["change_kwh"].abs()
    return out.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)
