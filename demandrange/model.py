"""The forecaster: three models that predict the low, middle and high case.

Some inputs are optional in the real world (night-time light needs a map file;
household energy spend needs a survey). The model is trained to cope when they
are missing, and it widens its range when they are.
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from .config import MODEL_COLUMNS, QUANTILES, SEED, TARGET

OPTIONAL = ["night_light", "energy_spend_usd"]


def completeness_level(df):
    """0 = all inputs known, 1 = no night light, 2 = no night light and no spend."""
    no_light = df["night_light"].isna().to_numpy()
    no_spend = df["energy_spend_usd"].isna().to_numpy()
    return np.where(no_light & no_spend, 2, np.where(no_light | no_spend, 1, 0))


def _mask(df, level):
    out = df.copy()
    if level >= 1:
        out["night_light"] = np.nan
    if level >= 2:
        out["energy_spend_usd"] = np.nan
    return out


class DemandRangeModel:
    """Predicts kWh per customer per month as a range (P10, P50, P90).

    P10 = a low case (9 in 10 sites do better), P50 = the middle case,
    P90 = a high case (only 1 in 10 sites does better).
    """

    def __init__(self, max_iter=300, max_depth=3, learning_rate=0.05,
                 min_samples_leaf=60, seed=SEED):
        self.params = dict(max_iter=max_iter, max_depth=max_depth,
                           learning_rate=learning_rate,
                           min_samples_leaf=min_samples_leaf, random_state=seed)
        self.models = {}
        self.widen = {0: 0.0, 1: 0.0, 2: 0.0}  # extra width (kWh) per completeness level
        self.seed = seed
        self.meta = {"data_source": "unknown", "n_sites": None, "n_rows": None}

    def _fit_quantiles(self, df):
        # Train on the full table plus copies with optional inputs hidden, so the
        # model learns what to do when they are missing.
        aug = pd.concat([df, _mask(df, 1), _mask(df, 2)], ignore_index=True)
        X, y = aug[MODEL_COLUMNS], aug[TARGET]
        models = {}
        for q in QUANTILES:
            m = HistGradientBoostingRegressor(loss="quantile", quantile=q, **self.params)
            m.fit(X, y)
            models[q] = m
        return models

    def fit(self, df, calibrate=True):
        """Train, then calibrate so the P10-P90 range really covers ~80%.

        Calibration: hold out 20% of villages, hide inputs at each completeness
        level, measure how often the range misses, and widen it by just enough
        (a simple 'conformal' step), separately for each level.
        """
        self.widen = {0: 0.0, 1: 0.0, 2: 0.0}
        self.meta["n_rows"] = int(len(df))
        if "site_id" in df.columns:
            self.meta["n_sites"] = int(df["site_id"].nunique())
        # Small real datasets need small leaves, or the trees cannot split at all.
        self.params["min_samples_leaf"] = int(min(self.params["min_samples_leaf"],
                                                  max(5, len(df) // 10)))
        n_sites = self.meta.get("n_sites") or 0
        self.meta["small_data"] = bool(n_sites and n_sites < 30)
        if calibrate and 6 <= n_sites < 20:
            self._calibrate_out_of_fold(df)
        elif calibrate and "site_id" in df.columns and n_sites >= 20:
            rng = np.random.default_rng(self.seed)
            sites = df["site_id"].unique()
            cal_sites = rng.choice(sites, size=max(5, len(sites) // 5), replace=False)
            is_cal = df["site_id"].isin(cal_sites)
            self.models = self._fit_quantiles(df[~is_cal])
            cal = df[is_cal]
            for level in (0, 1, 2):
                masked = _mask(cal, level)
                raw = self.predict(masked, _use_widen=False)
                miss = np.maximum(raw["p10"] - cal[TARGET], cal[TARGET] - raw["p90"])
                n = len(miss)
                q = min(1.0, np.ceil((n + 1) * 0.8) / n)
                self.widen[level] = float(max(0.0, np.quantile(miss, q)))
        self.models = self._fit_quantiles(df)
        return self

    def _calibrate_out_of_fold(self, df):
        """For small datasets: every site is predicted by a model that never saw it."""
        n_splits = min(5, df["site_id"].nunique())
        raw_parts = {lvl: [] for lvl in (0, 1, 2)}
        actual = []
        for tr, te in GroupKFold(n_splits=n_splits).split(df, groups=df["site_id"]):
            self.models = self._fit_quantiles(df.iloc[tr])
            test = df.iloc[te]
            actual.append(test[TARGET].to_numpy())
            for lvl in (0, 1, 2):
                raw_parts[lvl].append(self.predict(_mask(test, lvl), _use_widen=False))
        y = np.concatenate(actual)
        for lvl in (0, 1, 2):
            raw = pd.concat(raw_parts[lvl])
            miss = np.maximum(raw["p10"].to_numpy() - y, y - raw["p90"].to_numpy())
            n = len(miss)
            q = min(1.0, np.ceil((n + 1) * 0.8) / n)
            self.widen[lvl] = float(max(0.0, np.quantile(miss, q)))

    def predict(self, df, _use_widen=True):
        """Return a table with p10, p50, p90 (always in the right order)."""
        X = df[MODEL_COLUMNS]
        raw = np.column_stack([self.models[q].predict(X) for q in QUANTILES])
        raw = np.sort(raw, axis=1)  # stop low > middle > high mix-ups
        if _use_widen:
            w = np.array([self.widen[int(l)] for l in completeness_level(df)])
            raw[:, 0] -= w
            raw[:, 2] += w
        raw = np.clip(raw, 0.5, None)
        return pd.DataFrame(raw, columns=["p10", "p50", "p90"], index=df.index)

    def feature_importance(self, df=None, n=800):
        """Rough global importance by shuffling each input (needs some data)."""
        if df is None:
            return pd.Series(dtype=float)
        sample = df.sample(min(n, len(df)), random_state=0)
        base = np.abs(self.predict(sample)["p50"] - sample[TARGET]).mean()
        rng = np.random.default_rng(0)
        out = {}
        for c in MODEL_COLUMNS:
            shuffled = sample.copy()
            shuffled[c] = rng.permutation(shuffled[c].to_numpy())
            out[c] = max(0.0, np.abs(self.predict(shuffled)["p50"] - sample[TARGET]).mean() - base)
        s = pd.Series(out)
        return (s / s.sum() if s.sum() > 0 else s).sort_values(ascending=False)

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @staticmethod
    def load(path):
        return joblib.load(path)
