from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import requests
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet


# --- 1. LIVE DATA INGESTION ---
def fetch_live_weather_open_meteo(
    latitude=22.5726, longitude=88.3639, past_days=14, forecast_days=5
):
    """
    Fetches the past 14 days of history and 5 days of future forecast from Open-Meteo.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
        f"&past_days={past_days}&forecast_days={forecast_days}"
        "&daily=temperature_2m_max,temperature_2m_min,dew_point_2m_mean,"
        "shortwave_radiation_sum,wind_speed_10m_max"
        "&timezone=Asia/Kolkata"
    )
    response = requests.get(url).json()
    daily_data = response["daily"]

    # Structure into a dataframe
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily_data["time"]),
            "temperature_2m": (
                np.array(daily_data["temperature_2m_max"])
                + np.array(daily_data["temperature_2m_min"])
            )
            / 2,
            "dewpoint_temperature_2m": daily_data["dew_point_2m_mean"],
            # Convert MJ/m² to average W/m² roughly (1 MJ/m² = ~11.57 W/m² over 24h)
            "solar_rad_W_m2": np.array(daily_data["shortwave_radiation_sum"]) * 11.57,
            # Open-Meteo returns km/h, convert to m/s
            "wind_speed_m_s": np.array(daily_data["wind_speed_10m_max"]) * (5.0 / 18.0),
        }
    )

    # Set the dynamic sequence integer (time_idx) starting from 0 for the oldest day
    df["time_idx"] = range(len(df))
    return df


# --- 2. PHYSICS & WARD DOWNSCALING ---
def process_live_ward_physics(live_weather_df, static_ward_csv="kolkata_ward_static_features.csv"):
    """
    Cross-joins the single-point weather forecast with all 141 Kolkata wards,
    applying the UHI downscaling and WBGT physics formulas.
    """
    wards_df = pd.read_csv(static_ward_csv)
    wards_df["WARD"] = wards_df["WARD"].astype(str)

    # Cross join: duplicate the weather timeline for every single ward
    df_merged = wards_df.merge(live_weather_df, how="cross")

    # Base physics conversions
    df_merged["RH_percent"] = 100 * (
        np.exp(
            (17.625 * df_merged["dewpoint_temperature_2m"])
            / (243.04 + df_merged["dewpoint_temperature_2m"])
        )
        / np.exp((17.625 * df_merged["temperature_2m"]) / (243.04 + df_merged["temperature_2m"]))
    ).clip(1.0)

    # UHI Downscaling
    df_merged["UHI_Offset"] = (df_merged["LST_Celsius"] - df_merged["temperature_2m"]) * 0.15
    df_merged["Localized_Ta"] = df_merged["temperature_2m"] + df_merged["UHI_Offset"]

    # WBGT Simplification for speed
    ta = df_merged["Localized_Ta"]
    rh = df_merged["RH_percent"]
    df_merged["Tw_Celsius"] = (
        ta * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(ta + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * (rh**1.5) * np.arctan(0.023101 * rh)
        - 4.686035
    )
    df_merged["Tg_Celsius"] = (
        ta
        + (df_merged["solar_rad_W_m2"] / (0.15 * df_merged["wind_speed_m_s"].replace(0, 0.1) + 1.0))
        * 0.025
    )
    df_merged["WBGT_Celsius"] = (
        (0.7 * df_merged["Tw_Celsius"])
        + (0.2 * df_merged["Tg_Celsius"])
        + (0.1 * df_merged["Localized_Ta"])
    )

    # Add dummy target column (TFT requires the column to exist during inference, even if blank)
    df_merged["Human_Stress_Index"] = 0.0

    return df_merged


# --- 3. LIVE INFERENCE ---
def generate_live_predictions(
    df_live, model_ckpt_path="best_model.ckpt", output_csv="live_hsi_dashboard.csv"
):
    """
    Loads the dataloader configurations and outputs the 5-day boundary predictions.
    """
    # Create the prediction dataset using your exact training configuration
    prediction_dataset = TimeSeriesDataSet(
        df_live,
        time_idx="time_idx",
        target="Human_Stress_Index",
        group_ids=["WARD"],
        min_encoder_length=14,
        max_encoder_length=14,
        min_prediction_length=5,
        max_prediction_length=5,
        static_categoricals=["WARD"],
        static_reals=[
            "Pop_Density_per_sqkm",
            "Elderly_Percent",
            "Outdoor_Worker_Percent",
            "NDVI",
            "NDBI",
            "LST_Celsius",
        ],
        time_varying_known_reals=["time_idx"],
        time_varying_unknown_reals=[
            "wind_speed_m_s",
            "solar_rad_W_m2",
            "RH_percent",
            "Localized_Ta",
            "WBGT_Celsius",
            "Human_Stress_Index",
        ],
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )

    dataloader = prediction_dataset.to_dataloader(train=False, batch_size=128, num_workers=0)

    # Load model and predict
    best_tft = TemporalFusionTransformer.load_from_checkpoint(model_ckpt_path)
    raw_predictions = best_tft.predict(dataloader, mode="raw", return_x=True)
    preds_np = raw_predictions.output.prediction.detach().cpu().numpy()

    ward_identifiers = dataloader.dataset.decoded_index["WARD"].values

    records = []
    for ward_idx, ward_id in enumerate(ward_identifiers):
        for day in range(5):
            # Target date is calculated from today + the forecast offset
            target_date = (datetime.now(UTC) + timedelta(days=day + 1)).strftime(
                "%Y-%m-%d"
            )
            records.append(
                {
                    "WARD": ward_id,
                    "Forecast_Date": target_date,
                    "HSI_Best_Case": preds_np[ward_idx, day, 0],
                    "HSI_Expected": preds_np[ward_idx, day, 1],
                    "HSI_Worst_Case": preds_np[ward_idx, day, 2],
                }
            )

    # Save the live alerts directly for the frontend
    final_df = pd.DataFrame(records).round(2)
    final_df.to_csv(output_csv, index=False)
    print(
        f"Live predictions successfully generated for {len(final_df)} ward-days. Output saved to {output_csv}"
    )


if __name__ == "__main__":
    live_weather = fetch_live_weather_open_meteo()
    ward_matrix = process_live_ward_physics(live_weather)
    generate_live_predictions(ward_matrix, model_ckpt_path="path/to/your/best.ckpt")
