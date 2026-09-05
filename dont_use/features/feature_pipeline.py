"""Unified Feature Engineering and Spatial-Temporal Matrix Assembly.

Combines:
1. Hourly-to-diurnal weather metrics & thermal index calculation
2. Shift-based historical lags, rolling windows, and streak counters
3. Morphological Heat Vulnerability Index (HVI) & demographic vulnerability scoring
4. Full spatial-temporal dataset assembly pipeline
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from thermal.biophysics import (
    calculate_outdoor_wbgt,
    calculate_heat_index,
    calculate_utci,
    evaluate_nocturnal_recovery,
)


# ---------------------------------------------------------------------------
# 1. Vulnerability Scoring
# ---------------------------------------------------------------------------

def compute_morphological_hvi(
    tin_roofs: int,
    construction_sites: int,
    total_buildings: int,
    cooling_buffers: int,
    tin_weight: float = 1.5,
    construction_weight: float = 2.0,
    building_weight: float = 0.05,
    buffer_scale: float = 10.0,
) -> float:
    """Compute Heat Vulnerability Index (HVI) from urban morphology."""
    risk_load = (tin_weight * tin_roofs) + (construction_weight * construction_sites) + (building_weight * total_buildings)
    cooling_factor = buffer_scale * max(1, cooling_buffers) + 1.0
    return round(float(risk_load / cooling_factor), 3)


def compute_demographic_vulnerability_score(
    elderly_percentage: float,
    outdoor_worker_percentage: float,
    slum_percentage: float,
    healthcare_accessibility_score: float = 0.8,
) -> float:
    """Composite demographic vulnerability score."""
    score = (
        (elderly_percentage / 15.0) * 0.35
        + (outdoor_worker_percentage / 25.0) * 0.35
        + (slum_percentage / 30.0) * 0.30
    )
    return round(float(score / max(0.2, healthcare_accessibility_score)), 3)


# ---------------------------------------------------------------------------
# 2. Temporal Transforms
# ---------------------------------------------------------------------------

def add_weather_lags(
    df: pd.DataFrame,
    value_cols: Optional[List[str]] = None,
    lag_steps: Optional[List[int]] = None,
    group_col: str = "ward_id",
    time_col: str = "timestamp",
) -> pd.DataFrame:
    """Add historical lag columns strictly per ward."""
    if value_cols is None:
        value_cols = ["temperature_c", "wbgt_c"]
    if lag_steps is None:
        lag_steps = [1, 6, 12, 24]

    df_out = df.sort_values([group_col, time_col]).copy()
    grouped = df_out.groupby(group_col)
    for col in value_cols:
        if col in df_out.columns:
            for lag in lag_steps:
                df_out[f"{col}_lag_{lag}"] = grouped[col].shift(lag)
    return df_out


def add_rolling_features(
    df: pd.DataFrame,
    value_cols: Optional[List[str]] = None,
    windows: Optional[List[int]] = None,
    group_col: str = "ward_id",
    time_col: str = "timestamp",
) -> pd.DataFrame:
    """Add rolling averages computed strictly over past observations (shift 1)."""
    if value_cols is None:
        value_cols = ["temperature_c", "wbgt_c"]
    if windows is None:
        windows = [3, 7]

    df_out = df.sort_values([group_col, time_col]).copy()
    grouped = df_out.groupby(group_col)
    for col in value_cols:
        if col in df_out.columns:
            for win in windows:
                df_out[f"{col}_rolling_{win}"] = np.round(
                    grouped[col].transform(lambda s: s.shift(1).rolling(win, min_periods=1).mean()), 2
                )
    return df_out


def compute_consecutive_hot_days(
    daily_df: pd.DataFrame,
    temp_threshold_c: float = 40.0,
    wbgt_threshold_c: float = 30.0,
    group_col: str = "ward_id",
    time_col: str = "date",
) -> pd.DataFrame:
    """Calculate the consecutive sequence of days exceeding extreme thermal thresholds."""
    df_out = daily_df.sort_values([group_col, time_col]).copy()

    def _streak(series: pd.Series, thresh: float) -> pd.Series:
        is_above = (series >= thresh).astype(int)
        st = is_above * (is_above.groupby((is_above != is_above.shift(1)).cumsum()).cumcount() + 1)
        return st.shift(1).fillna(0).astype(int)

    if "peak_temperature_c" in df_out.columns:
        df_out["consecutive_hot_days"] = df_out.groupby(group_col)["peak_temperature_c"].transform(
            lambda s: _streak(s, temp_threshold_c)
        )
    if "peak_wbgt_c" in df_out.columns:
        df_out["consecutive_high_wbgt_days"] = df_out.groupby(group_col)["peak_wbgt_c"].transform(
            lambda s: _streak(s, wbgt_threshold_c)
        )
    return df_out


# ---------------------------------------------------------------------------
# 3. Diurnal & Full Matrix Extractor
# ---------------------------------------------------------------------------

class WeatherFeatureExtractor:
    """Extracts diurnal thermal stress metrics from hourly records."""

    NIGHT_HOURS = [22, 23, 0, 1, 2, 3, 4, 5]

    def extract_daily_diurnal_metrics(self, df_hourly: pd.DataFrame) -> pd.DataFrame:
        df = df_hourly.copy()
        if "wbgt_c" not in df.columns:
            df["wbgt_c"] = calculate_outdoor_wbgt(
                df["temperature_c"], df["relative_humidity_pct"], df["wind_speed_mps"], df["solar_radiation_wm2"]
            )
        if "heat_index_c" not in df.columns:
            df["heat_index_c"] = calculate_heat_index(df["temperature_c"], df["relative_humidity_pct"])
        if "utci_c" not in df.columns:
            df["utci_c"] = calculate_utci(
                df["temperature_c"], df["relative_humidity_pct"], df["wind_speed_mps"], df["solar_radiation_wm2"]
            )

        df["date"] = pd.to_datetime(df["timestamp"]).dt.date
        df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        records = []
        for (ward_id, d), group in df.groupby(["ward_id", "date"]):
            night_mask = group["hour"].isin(self.NIGHT_HOURS)
            min_night = round(float(group[night_mask]["temperature_c"].min()), 2) if np.any(night_mask) else round(float(group["temperature_c"].min()), 2)
            nocturnal = evaluate_nocturnal_recovery(min_night)

            records.append({
                "ward_id": ward_id,
                "date": d,
                "peak_temperature_c": round(float(group["temperature_c"].max()), 2),
                "mean_temperature_c": round(float(group["temperature_c"].mean()), 2),
                "min_night_temp_c": min_night,
                "is_night_recovery_deficit": nocturnal["is_recovery_deficit"],
                "night_recovery_deficit_c": nocturnal["recovery_deficit_degrees_c"],
                "peak_wbgt_c": round(float(group["wbgt_c"].max()), 2),
                "mean_wbgt_c": round(float(group["wbgt_c"].mean()), 2),
                "peak_utci_c": round(float(group["utci_c"].max()), 2),
                "peak_heat_index_c": round(float(group["heat_index_c"].max()), 2),
                "avg_relative_humidity_pct": round(float(group["relative_humidity_pct"].mean()), 1),
                "mean_wind_speed_mps": round(float(group["wind_speed_mps"].mean()), 2),
                "is_forecast": bool(group["is_forecast"].any()),
            })
        return pd.DataFrame(records)


class UnifiedFeaturePipeline:
    """Assembles all features into a consolidated ward-time matrix."""

    def __init__(self):
        self.weather_ext = WeatherFeatureExtractor()

    def assemble_ward_time_features(
        self,
        df_weather_hourly: pd.DataFrame,
        df_spatial_features: pd.DataFrame,
        df_health_daily: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        df_daily = self.weather_ext.extract_daily_diurnal_metrics(df_weather_hourly)
        df_daily = compute_consecutive_hot_days(df_daily, time_col="date")
        df_daily = add_rolling_features(
            df_daily,
            value_cols=["peak_temperature_c", "peak_wbgt_c", "min_night_temp_c"],
            windows=[3, 7],
            time_col="date",
        )

        df_merged = pd.merge(df_daily, df_spatial_features, on="ward_id", how="left")

        if df_health_daily is not None:
            health_shifted = df_health_daily.sort_values(["spatial_id", "date"]).copy()
            grp = health_shifted.groupby("spatial_id")
            health_shifted["mortality_lag_1d"] = grp["all_cause_mortality"].shift(1)
            health_shifted["hospitalization_lag_1d"] = grp["emergency_hospitalizations"].shift(1)
            health_shifted["hospitalization_rolling_7d"] = grp["emergency_hospitalizations"].transform(
                lambda s: s.shift(1).rolling(7, min_periods=1).mean()
            )
            health_shifted = health_shifted.rename(columns={"spatial_id": "ward_id"})
            df_merged = pd.merge(df_merged, health_shifted, on=["ward_id", "date"], how="left")

        return df_merged
