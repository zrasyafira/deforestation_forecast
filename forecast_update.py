"""Regenerate the historical + forecast dataset used by the dashboard.

Inputs (produced by notebooks/deforestation_revised.ipynb):
  data/history_ready.csv   historical loss and GFW gross emissions per province-year
  model/xgb_model.json     final XGBoost model (target: log1p(loss_ha))
  model/metadata.json      features, lags, windows, horizon, emission factors

Output:
  data/deforestation_historical_forecast_full.csv
  columns: subnational1, year, loss_ha, loss_rate_%, emission_CO2e, source

The feature logic must stay identical to make_features() in the notebook.
"""
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = os.path.dirname(os.path.abspath(__file__))
HIST_PATH = os.path.join(ROOT, "data", "history_ready.csv")
MODEL_PATH = os.path.join(ROOT, "model", "xgb_model.json")
META_PATH = os.path.join(ROOT, "model", "metadata.json")
OUTPUT_PATH = os.path.join(ROOT, "data", "deforestation_historical_forecast_full.csv")
COLS = ["subnational1", "year", "loss_ha", "loss_rate_%", "emission_CO2e", "source"]

with open(META_PATH) as fh:
    META = json.load(fh)
LAGS, WINDOWS, FEATURES = META["lags"], META["windows"], META["features"]


def make_features(d):
    d = d.sort_values(["subnational1", "year"]).reset_index(drop=True).copy()
    g = d.groupby("subnational1")["log_loss"]
    for k in LAGS:
        d[f"lag_{k}"] = g.shift(k)
    for w in WINDOWS:
        d[f"roll_mean_{w}"] = g.transform(lambda s: s.shift(1).rolling(w).mean())
        d[f"roll_std_{w}"] = g.transform(lambda s: s.shift(1).rolling(w).std())
    d["diff_1"] = d["lag_1"] - d["lag_2"]
    d["diff_3"] = d["lag_1"] - d["lag_3"]
    d["log_extent"] = np.log1p(d["extent_2000_ha"])
    return d


def recursive_forecast(model, base, horizon):
    d = base[["subnational1", "year", "extent_2000_ha", "log_loss"]].copy()
    last = int(d["year"].max())
    preds = []
    for step in range(1, horizon + 1):
        y = last + step
        nxt = d[d["year"] == y - 1][["subnational1", "extent_2000_ha"]].assign(year=y, log_loss=np.nan)
        d = pd.concat([d, nxt], ignore_index=True)
        f = make_features(d)
        row = f[f["year"] == y]
        p = dict(zip(row["subnational1"], model.predict(xgb.DMatrix(row[FEATURES]))))
        mask = d["year"] == y
        d.loc[mask, "log_loss"] = d.loc[mask, "subnational1"].map(p)
        preds.append(d[mask])
    out = pd.concat(preds)
    out["loss_ha"] = np.clip(np.expm1(out["log_loss"]), 0, None)
    return out


def main():
    hist = pd.read_csv(HIST_PATH)
    hist["log_loss"] = np.log1p(hist["loss_ha"])
    model = xgb.Booster()
    model.load_model(MODEL_PATH)

    fc = recursive_forecast(model, hist, META["horizon"])
    fc["loss_rate_%"] = fc["loss_ha"] / fc["extent_2000_ha"] * 100
    factor = pd.Series(META["emission_factor_Mg_CO2e_per_ha"])
    fc["emission_CO2e"] = fc["loss_ha"] * fc["subnational1"].map(factor)

    full = pd.concat(
        [hist.assign(source="historical")[COLS], fc.assign(source="forecast")[COLS]],
        ignore_index=True,
    ).sort_values(["subnational1", "year"])
    full.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(full)} rows ({full['source'].value_counts().to_dict()}) to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
