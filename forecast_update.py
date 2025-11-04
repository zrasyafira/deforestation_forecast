import pandas as pd
import xgboost as xgb
import numpy as np
import os
from datetime import datetime

# ========== Konfigurasi Path ==========
MODEL_PATH = "model/xgb_optimized.json"
FEATURE_PATH = "data/deforestation_features_ready.csv"
HIST_PATH = "data/deforestation_carbon_ready.csv"
OUTPUT_PATH = "data/deforestation_historical_forecast_full.csv"
FORECAST_YEARS = 6  # 2025–2030

# ========== Load Model dan Dataset ==========
print("[INFO] Loading model and datasets...")
model = xgb.Booster()
model.load_model(MODEL_PATH)

df = pd.read_csv(FEATURE_PATH)
df_hist = pd.read_csv(HIST_PATH)

FEATURES = [
    'lag_1','lag_2','lag_3','lag_5','lag_7','lag_10',
    'roll_mean_3','roll_mean_5','roll_mean_7','roll_mean_10',
    'roll_std_3','roll_std_5','roll_std_7','roll_std_10',
    'pct_change_3','pct_change_5','pct_change_7','pct_change_10',
    'year','trend','sin_year','cos_year',
    'extent_2000_ha','avg_gfw_aboveground_carbon_stocks_2000__Mg_C_ha-1',
    'prov_enc','prov_mean_loss'
]

latest_year = int(df['year'].max())
last_rows = df.sort_values(["subnational1", "year"]).groupby("subnational1").tail(1)
forecast_results = []

print(f"Generating forecast for {FORECAST_YEARS} years ahead...")

for step in range(1, FORECAST_YEARS + 1):
    next_year = latest_year + step
    next_pred_features = last_rows[FEATURES].copy()
    next_pred_features["year"] = next_year
    next_pred_features["trend"] = next_pred_features["trend"] + 1
    next_pred_features["sin_year"] = np.sin(2 * np.pi * next_year / 10)
    next_pred_features["cos_year"] = np.cos(2 * np.pi * next_year / 10)

    dnext = xgb.DMatrix(next_pred_features)
    pred = np.expm1(model.predict(dnext))

    next_pred = last_rows.copy()
    next_pred["predicted_loss_ha"] = pred
    next_pred["predicted_loss_rate_%"] = (pred / next_pred["extent_2000_ha"]) * 100
    next_pred["predicted_emission_CO2e"] = pred * next_pred["avg_gfw_aboveground_carbon_stocks_2000__Mg_C_ha-1"] * 3.67
    next_pred["year"] = next_year
    next_pred["source"] = "forecast"
    forecast_results.append(next_pred)

    # update lag agar tahun berikutnya bisa lanjut prediksi
    for lag in [10, 7, 5, 3, 2, 1]:
        last_rows[f"lag_{lag}"] = next_pred["predicted_loss_ha"]

forecast_df = pd.concat(forecast_results, ignore_index=True)
forecast_df = forecast_df[[
    "subnational1", "year", "predicted_loss_ha",
    "predicted_loss_rate_%", "predicted_emission_CO2e",
    "extent_2000_ha", "avg_gfw_aboveground_carbon_stocks_2000__Mg_C_ha-1", "source"
]]

# === Gabungkan dengan Historis ===
print("Merging forecast with historical data...")
df_hist["source"] = "historical"

combined = pd.concat([df_hist, forecast_df], ignore_index=True, sort=False)
combined["loss_rate_%"] = data_all["loss_rate_%"].combine_first(data_all["predicted_loss_rate_%"])
combined["loss_ha"] = data_all["loss_ha"].combine_first(data_all["predicted_loss_ha"])
combined["emission_CO2e"] = data_all["emission_estimated_CO2e"].combine_first(data_all["predicted_emission_CO2e"])

cols_save = [
    "subnational1", "year", "predicted_loss_ha",
    "predicted_loss_rate_%", "predicted_emission_CO2e"
]
forecast_data = combined[cols_save]

combined.to_csv(OUTPUT_PATH, index=False)
print(f"Dataset updated and saved to {OUTPUT_PATH} at {datetime.now()}")
