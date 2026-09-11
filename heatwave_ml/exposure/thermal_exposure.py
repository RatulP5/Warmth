"""
heatwave_ml/exposure/thermal_exposure.py
────────────────────────────────────────
Aggregates hourly meteorological and biophysical thermal indices
into daily ward-level exposure metrics:
  - Daily maximum and mean WBGT & UTCI
  - Nocturnal heat stress (nighttime WBGT & temperature)
  - Heatwave persistence (consecutive days of extreme thermal stress)
  - Cumulative 72-hour thermal load
"""

import pandas as pd
import numpy as np

try:
    from . import config as cfg
except ImportError:
    import config as cfg


class ThermalExposureAggregator:
    """
    Transforms hourly ward-mapped weather and thermal indices into
    daily exposure metrics required for heat health monitoring.
    """

    def __init__(self, weather_path: str = cfg.WEATHER_PROCESSED_PATH):
        self.weather_path = weather_path

    def process(self, ward_ids: list[str] | None = None) -> pd.DataFrame:
        """
        Load processed weather features and aggregate to daily ward level.
        """
        df = pd.read_parquet(self.weather_path)
        if ward_ids:
            df = df[df["ward_id"].isin(ward_ids)].copy()

        df["date"] = df["timestamp"].dt.date
        df["is_nighttime"] = df["is_nighttime"].astype(bool)
        df["tropical_night_failure"] = df["tropical_night_failure"].astype(bool)

        # 1. Base daily aggregations
        daily_records = []
        grouped = df.groupby(["ward_id", "date"])

        for (wid, dt), group in grouped:
            night_group = group[group["is_nighttime"]]
            nocturnal_wbgt = (
                round(float(night_group["WBGT"].mean()), 2)
                if not night_group.empty and not night_group["WBGT"].isna().all()
                else np.nan
            )
            nocturnal_temp = (
                round(float(night_group["temperature"].mean()), 2)
                if not night_group.empty and not night_group["temperature"].isna().all()
                else np.nan
            )

            wbgt_max = round(float(group["WBGT"].max()), 2)
            wbgt_mean = round(float(group["WBGT"].mean()), 2)
            utci_max = round(float(group["UTCI"].max()), 2)
            utci_mean = round(float(group["UTCI"].mean()), 2)
            temp_max = round(float(group["temperature"].max()), 2)
            temp_mean = round(float(group["temperature"].mean()), 2)

            # Cumulative stress degree-hours above baseline (e.g. 28 degC WBGT)
            stress_hours = (group["WBGT"] - cfg.WBGT_STRESS_BASE).clip(lower=0.0).sum()

            daily_records.append({
                "ward_id":                   wid,
                "date":                      pd.to_datetime(dt),
                "temp_daily_max":            temp_max,
                "temp_daily_mean":           temp_mean,
                "wbgt_daily_max":            wbgt_max,
                "wbgt_daily_mean":           wbgt_mean,
                "utci_daily_max":            utci_max,
                "utci_daily_mean":           utci_mean,
                "nocturnal_wbgt_mean":       nocturnal_wbgt,
                "nocturnal_temp_mean":       nocturnal_temp,
                "tropical_night_flag":       bool(group["tropical_night_failure"].any()),
                "daily_stress_degree_hours": round(float(stress_hours), 2),
                "relative_humidity_mean":    round(float(group["relative_humidity"].mean()), 1),
                "solar_radiation_sum":       round(float(group["solar_radiation"].sum()), 1),
            })

        daily_df = pd.DataFrame(daily_records)
        daily_df.sort_values(["ward_id", "date"], inplace=True)

        # 2. Sequential rolling metrics per ward
        # - Heatwave persistence: count of consecutive days with wbgt_daily_max >= threshold
        # - Cumulative 72-hour stress
        def _calc_ward_metrics(gdf: pd.DataFrame) -> pd.DataFrame:
            gdf = gdf.copy()
            # Persistence streak
            is_hot = gdf["wbgt_daily_max"] >= cfg.WBGT_HEATWAVE_THRESHOLD
            streak = []
            cur = 0
            for hot in is_hot:
                if hot:
                    cur += 1
                else:
                    cur = 0
                streak.append(cur)
            gdf["heatwave_persistence_days"] = streak

            # 3-day (72h) rolling cumulative stress degree hours
            gdf["cumulative_thermal_stress_72h"] = (
                gdf["daily_stress_degree_hours"]
                .rolling(window=3, min_periods=1)
                .sum()
                .round(2)
            )

            # 3-day rolling count of tropical nights
            gdf["tropical_night_count_3d"] = (
                gdf["tropical_night_flag"]
                .astype(int)
                .rolling(window=3, min_periods=1)
                .sum()
                .astype(int)
            )
            return gdf

        processed_chunks = []
        for _, ward_chunk in daily_df.groupby("ward_id", sort=False):
            processed_chunks.append(_calc_ward_metrics(ward_chunk))
        daily_df = pd.concat(processed_chunks, ignore_index=True)
        return daily_df
