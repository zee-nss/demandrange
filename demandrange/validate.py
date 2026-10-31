"""Validation on villages the model has never seen (the brief's Impact metric).

Two tests:
1. Held-out sites: every village is predicted by a model that never saw it.
2. Held-out regions: a whole region is hidden (a stand-in for 'a new country').
Compared with a simple baseline: 'every village gets the average demand'.
"""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from .config import REPORT_DIR, TARGET
from .model import DemandRangeModel


def _metrics(actual, pred, baseline):
    mae = float(np.mean(np.abs(actual - pred["p50"])))
    mae_base = float(np.mean(np.abs(actual - baseline)))
    mape = float(np.mean(np.abs(actual - pred["p50"]) / actual) * 100)
    coverage = float(np.mean((actual >= pred["p10"]) & (actual <= pred["p90"])) * 100)
    return {
        "mae_kwh": round(mae, 2),
        "mape_pct": round(mape, 1),
        "baseline_mae_kwh": round(mae_base, 2),
        "improvement_vs_baseline_pct": round((1 - mae / mae_base) * 100, 1),
        "range_coverage_pct": round(coverage, 1),  # ideal is about 80
        "rows_tested": int(len(actual)),
    }


def _out_of_fold(df, groups, n_splits, hide=()):
    preds = pd.DataFrame(index=df.index, columns=["p10", "p50", "p90"], dtype=float)
    baseline = pd.Series(index=df.index, dtype=float)
    for train_idx, test_idx in GroupKFold(n_splits=n_splits).split(df, groups=groups):
        train, test = df.iloc[train_idx], df.iloc[test_idx]
        model = DemandRangeModel().fit(train)
        test_in = test.copy()
        for c in hide:
            test_in[c] = float('nan')
        preds.iloc[test_idx] = model.predict(test_in).values
        baseline.iloc[test_idx] = train[TARGET].mean()
    return preds, baseline


def run_validation(df, save=True):
    """Return a dict of results and (optionally) save JSON and a chart."""
    n_regions = df["region"].nunique()
    n_sites = df["site_id"].nunique()
    if n_sites < 5:
        raise ValueError(f"Need at least 5 sites to validate, found {n_sites}. Add more sites.")

    site_pred, site_base = _out_of_fold(df, df["site_id"], n_splits=5)
    sites_result = _metrics(df[TARGET], site_pred, site_base)

    live_pred, live_base = _out_of_fold(df, df["site_id"], n_splits=5,
                                        hide=("night_light", "energy_spend_usd"))
    live_result = _metrics(df[TARGET], live_pred, live_base)

    if n_regions >= 2:
        region_pred, region_base = _out_of_fold(df, df["region"], n_splits=min(n_regions, 6))
        region_result = _metrics(df[TARGET], region_pred, region_base)
    else:
        region_result = {"note": "Only one region in the data, so the new-region test was skipped."}

    # Growth check: does the model get the year-0 to year-3 rise right?
    y0, y3 = df["years_since_connection"] == 0, df["years_since_connection"] == 3
    if y0.any() and y3.any():
        actual_growth = df.loc[y3, TARGET].mean() / df.loc[y0, TARGET].mean() - 1
        pred_growth = site_pred.loc[y3, "p50"].mean() / site_pred.loc[y0, "p50"].mean() - 1
    else:
        actual_growth = pred_growth = float("nan")

    result = {
        "held_out_sites": sites_result,
        "held_out_regions": region_result,
        "held_out_sites_map_inputs_only": live_result,
        "growth_year0_to_year3_pct": {
            "actual": None if actual_growth != actual_growth else round(float(actual_growth) * 100, 1),
            "predicted": None if pred_growth != pred_growth else round(float(pred_growth) * 100, 1),
        },
        "data_note": ("Computed on simulated data unless you loaded your own "
                      "CSV. Real metered data is needed before relying on it."),
    }
    if save:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        (REPORT_DIR / "validation.json").write_text(json.dumps(result, indent=2))
        _plot(df, site_pred, REPORT_DIR / "validation.png")
    return result


def _plot(df, pred, path):
    """Predicted range vs actual demand for 60 random held-out rows."""
    rng = np.random.default_rng(0)
    idx = rng.choice(df.index, size=min(60, len(df)), replace=False)
    actual = df.loc[idx, TARGET].values
    p = pred.loc[idx]
    order = np.argsort(actual)
    actual, p = actual[order], p.iloc[order]
    fig, ax = plt.subplots(figsize=(6.4, 4.4), dpi=140)
    ax.vlines(actual, p["p10"], p["p90"], color="#9CC9C6", lw=2, label="Predicted range (P10 to P90)")
    ax.scatter(actual, p["p50"], s=14, color="#0B7A75", label="Predicted middle case (P50)", zorder=3)
    lim = [min(actual.min(), p["p10"].min()) - 1, max(actual.max(), p["p90"].max()) + 1]
    ax.plot(lim, lim, color="#14213D", lw=1, ls="--", label="Perfect prediction")
    ax.set_xlabel("Actual demand (kWh per customer per month)")
    ax.set_ylabel("Predicted demand (kWh per customer per month)")
    ax.set_title("Villages the model had never seen", loc="left", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
