"""Unified Weather Data Ingestion Adapter.

Ingests:
1. Historical meteorological observations (Open-Meteo Archive API)
2. Numerical weather forecasts up to 7 days (Open-Meteo Forecast API)
Includes offline synthetic demo generators with provenance tracking.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import requests
import pandas as pd
import numpy as np


class HistoricalWeatherClient:
    """Client for historical meteorological observations."""

    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    def __init__(self, timeout_sec: int = 25, user_agent: str = "HeatwaveAIWeatherClient/1.0"):
        self.timeout_sec = timeout_sec
        self.headers = {"User-Agent": user_agent}

    def fetch_historical(
        self,
        ward_id: str,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        demo_mode: bool = False,
    ) -> pd.DataFrame:
        """Fetch historical hourly weather."""
        if demo_mode:
            return self._generate_synthetic_historical(ward_id, lat, lon, start_date, end_date)

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "direct_normal_irradiance",
                "surface_pressure",
                "precipitation",
            ],
            "timezone": "Asia/Kolkata",
        }
        try:
            resp = requests.get(self.ARCHIVE_URL, params=params, headers=self.headers, timeout=self.timeout_sec)
            resp.raise_for_status()
            payload = resp.json().get("hourly", {})
            df = pd.DataFrame({
                "ward_id": ward_id,
                "timestamp": pd.to_datetime(payload["time"]),
                "temperature_c": payload["temperature_2m"],
                "relative_humidity_pct": payload["relative_humidity_2m"],
                "wind_speed_mps": [w / 3.6 for w in payload["wind_speed_10m"]],
                "solar_radiation_wm2": payload["direct_normal_irradiance"],
                "surface_pressure_hpa": payload.get("surface_pressure", [1013.25] * len(payload["time"])),
                "precipitation_mm": payload.get("precipitation", [0.0] * len(payload["time"])),
                "is_forecast": False,
            })
            df.attrs["provenance"] = {
                "source": "Open-Meteo Historical Archive",
                "retrieval_time": datetime.utcnow().isoformat(),
            }
            return df
        except Exception:
            return self._generate_synthetic_historical(ward_id, lat, lon, start_date, end_date)

    def _generate_synthetic_historical(
        self, ward_id: str, lat: float, lon: float, start_date: str, end_date: str
    ) -> pd.DataFrame:
        timestamps = pd.date_range(start=f"{start_date} 00:00:00", end=f"{end_date} 23:00:00", freq="h")
        n = len(timestamps)
        hour = timestamps.hour.values
        solar_curve = np.maximum(0.0, np.sin(np.pi * (hour - 6) / 12))
        solar_radiation = solar_curve * (800.0 + np.random.uniform(-50.0, 100.0, n))

        temp_cycle = np.sin(np.pi * (hour - 8) / 12)
        base_temp = 31.0 + 7.0 * temp_cycle + np.random.normal(0.0, 1.0, n)
        humidity = np.clip(85.0 - 35.0 * temp_cycle + np.random.normal(0.0, 3.0, n), 25.0, 95.0)
        wind_speed = np.clip(2.5 + np.random.normal(0.0, 0.8, n), 0.5, 12.0)

        df = pd.DataFrame({
            "ward_id": ward_id,
            "timestamp": timestamps,
            "temperature_c": np.round(base_temp, 2),
            "relative_humidity_pct": np.round(humidity, 1),
            "wind_speed_mps": np.round(wind_speed, 2),
            "solar_radiation_wm2": np.round(solar_radiation, 1),
            "surface_pressure_hpa": np.round(1008.0 + np.random.normal(0.0, 2.0, n), 1),
            "precipitation_mm": np.zeros(n),
            "is_forecast": False,
        })
        df.attrs["provenance"] = {
            "source": "Synthetic Climatological Demo Generator",
            "retrieval_time": datetime.utcnow().isoformat(),
        }
        return df


class WeatherForecastClient:
    """Client for numerical weather forecast ingestion."""

    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout_sec: int = 20, user_agent: str = "HeatwaveAIForecastClient/1.0"):
        self.timeout_sec = timeout_sec
        self.headers = {"User-Agent": user_agent}

    def fetch_forecast(
        self,
        ward_id: str,
        lat: float,
        lon: float,
        forecast_days: int = 5,
        demo_mode: bool = False,
    ) -> pd.DataFrame:
        """Fetch hourly weather forecast up to `forecast_days`."""
        if demo_mode:
            return self._generate_synthetic_forecast(ward_id, lat, lon, forecast_days)

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "direct_normal_irradiance",
                "surface_pressure",
                "precipitation",
            ],
            "forecast_days": forecast_days,
            "timezone": "Asia/Kolkata",
        }
        try:
            resp = requests.get(self.FORECAST_URL, params=params, headers=self.headers, timeout=self.timeout_sec)
            resp.raise_for_status()
            payload = resp.json().get("hourly", {})
            df = pd.DataFrame({
                "ward_id": ward_id,
                "timestamp": pd.to_datetime(payload["time"]),
                "temperature_c": payload["temperature_2m"],
                "relative_humidity_pct": payload["relative_humidity_2m"],
                "wind_speed_mps": [w / 3.6 for w in payload["wind_speed_10m"]],
                "solar_radiation_wm2": payload["direct_normal_irradiance"],
                "surface_pressure_hpa": payload.get("surface_pressure", [1013.25] * len(payload["time"])),
                "precipitation_mm": payload.get("precipitation", [0.0] * len(payload["time"])),
                "is_forecast": True,
            })
            df.attrs["provenance"] = {
                "source": "Open-Meteo GFS/ECMWF Numerical Forecast",
                "retrieval_time": datetime.utcnow().isoformat(),
            }
            return df
        except Exception:
            return self._generate_synthetic_forecast(ward_id, lat, lon, forecast_days)

    def _generate_synthetic_forecast(
        self, ward_id: str, lat: float, lon: float, forecast_days: int = 5
    ) -> pd.DataFrame:
        start_ts = pd.Timestamp.now(tz="Asia/Kolkata").floor("h")
        timestamps = pd.date_range(start=start_ts, periods=forecast_days * 24, freq="h")
        n = len(timestamps)
        hour = timestamps.hour.values
        solar_curve = np.maximum(0.0, np.sin(np.pi * (hour - 6) / 12))
        solar_radiation = solar_curve * (850.0 + np.random.uniform(-40.0, 80.0, n))

        day_progression = np.linspace(0.0, 1.0, n)
        heatwave_amp = 3.0 * np.sin(np.pi * day_progression)
        temp_cycle = np.sin(np.pi * (hour - 8) / 12)
        base_temp = 33.0 + heatwave_amp + 8.0 * temp_cycle + np.random.normal(0.0, 0.8, n)
        humidity = np.clip(80.0 - 30.0 * temp_cycle + np.random.normal(0.0, 2.5, n), 28.0, 92.0)
        wind_speed = np.clip(2.2 + np.random.normal(0.0, 0.7, n), 0.5, 9.0)

        df = pd.DataFrame({
            "ward_id": ward_id,
            "timestamp": timestamps.tz_localize(None),
            "temperature_c": np.round(base_temp, 2),
            "relative_humidity_pct": np.round(humidity, 1),
            "wind_speed_mps": np.round(wind_speed, 2),
            "solar_radiation_wm2": np.round(solar_radiation, 1),
            "surface_pressure_hpa": np.round(1006.0 + np.random.normal(0.0, 1.5, n), 1),
            "precipitation_mm": np.zeros(n),
            "is_forecast": True,
        })
        df.attrs["provenance"] = {
            "source": "Synthetic Forecast Demo Generator",
            "retrieval_time": datetime.utcnow().isoformat(),
        }
        return df
