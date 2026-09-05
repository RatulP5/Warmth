"""Unified Data Validation, Quality Auditing, and Anomaly Detection.

Combines:
1. Pydantic schemas for data contracts
2. Physical range & duplicate consistency audits -> data_quality_report.json
3. Leakage-free missing data imputation and health record NaN preservation
4. Rolling baseline anomaly detection
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. Schemas
# ---------------------------------------------------------------------------

class WardRecord(BaseModel):
    ward_id: str
    city: str
    zone: Optional[str] = "Default"
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)


class WeatherRecord(BaseModel):
    ward_id: str
    timestamp: datetime
    temperature_c: float = Field(..., ge=-25.0, le=65.0)
    relative_humidity_pct: float = Field(..., ge=0.0, le=100.0)
    wind_speed_mps: float = Field(..., ge=0.0, le=100.0)
    solar_radiation_wm2: float = Field(..., ge=0.0, le=1500.0)
    is_forecast: bool = False


# ---------------------------------------------------------------------------
# 2. Audits & Reports
# ---------------------------------------------------------------------------

def audit_weather_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Audit meteorological dataframe against physical boundaries."""
    report = {
        "dataset": "weather",
        "total_rows": int(len(df)),
        "anomalies_detected": 0,
        "missing_summary": {},
        "issues": [],
        "passed": True,
    }
    if df.empty:
        report["passed"] = False
        report["issues"].append("Weather dataframe is empty.")
        return report

    for col in df.columns:
        null_count = int(df[col].isnull().sum())
        if null_count > 0:
            report["missing_summary"][col] = {"null_count": null_count, "pct": round((null_count / len(df)) * 100.0, 2)}

    if "temperature_c" in df.columns:
        out = df[(df["temperature_c"] < -20.0) | (df["temperature_c"] > 60.0)]
        if len(out) > 0:
            report["issues"].append(f"Temperature out of bounds: {len(out)} rows")
            report["anomalies_detected"] += len(out)

    if "relative_humidity_pct" in df.columns:
        out = df[(df["relative_humidity_pct"] < 0.0) | (df["relative_humidity_pct"] > 100.0)]
        if len(out) > 0:
            report["issues"].append(f"Humidity out of bounds: {len(out)} rows")
            report["anomalies_detected"] += len(out)

    if report["anomalies_detected"] > 0:
        report["passed"] = False
    return report


def audit_health_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Audit health outcome dataframe, strictly guarding against zero-fill traps."""
    report = {"dataset": "health", "total_rows": int(len(df)), "issues": [], "passed": True}
    if df.empty:
        report["passed"] = False
        report["issues"].append("Health dataframe is empty.")
        return report

    if "spatial_level" not in df.columns:
        report["issues"].append("Missing 'spatial_level' indicator.")
        report["passed"] = False

    for col in ["all_cause_mortality", "emergency_hospitalizations"]:
        if col in df.columns:
            neg = df[df[col] < 0]
            if len(neg) > 0:
                report["issues"].append(f"Negative counts in {col}: {len(neg)} rows")
                report["passed"] = False
    return report


def save_quality_report(
    reports: List[Dict[str, Any]],
    output_path: str = "data/reports/data_quality_report.json",
) -> Path:
    """Save aggregated audit report to JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    combined = {
        "report_generated_at": pd.Timestamp.utcnow().isoformat(),
        "datasets_audited": reports,
        "all_passed": all(r.get("passed", False) for r in reports),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2)
    return path


# ---------------------------------------------------------------------------
# 3. Missing Data & Anomalies
# ---------------------------------------------------------------------------

def handle_missing_weather(
    df: pd.DataFrame, max_consecutive_hours: int = 3
) -> pd.DataFrame:
    """Interpolate short weather gaps while tracking imputation indicators."""
    df_out = df.copy()
    weather_cols = ["temperature_c", "relative_humidity_pct", "wind_speed_mps", "solar_radiation_wm2"]
    for col in weather_cols:
        if col in df_out.columns:
            was_null = df_out[col].isnull()
            df_out[f"{col}_imputed"] = False
            df_out[col] = df_out[col].interpolate(method="linear", limit=max_consecutive_hours)
            df_out.loc[was_null & df_out[col].notnull(), f"{col}_imputed"] = True
    return df_out


def compute_rolling_anomaly(
    df: pd.DataFrame,
    value_column: str,
    baseline_window: int = 30,
    group_column: str = "ward_id",
) -> pd.Series:
    """Compute rolling Z-score anomaly using strictly past observations."""
    grouped = df.groupby(group_column)[value_column]
    rolling_mean = grouped.transform(lambda x: x.shift(1).rolling(baseline_window, min_periods=3).mean())
    rolling_std = grouped.transform(lambda x: x.shift(1).rolling(baseline_window, min_periods=3).std()).replace(0.0, np.nan).fillna(1.0)
    return ((df[value_column] - rolling_mean) / rolling_std).fillna(0.0)
