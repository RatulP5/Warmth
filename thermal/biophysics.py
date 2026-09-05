"""Unified Biophysical Thermal Stress Engine.

Provides deterministic thermodynamic calculations:
- Stull (2011) psychrometric natural wet-bulb temperature (Tw)
- Black globe temperature (Tg) under solar irradiance and wind convective cooling
- ISO 7243 outdoor and indoor Wet-Bulb Globe Temperature (WBGT)
- Universal Thermal Climate Index (UTCI) operational polynomial
- NOAA Rothfusz Heat Index regression
- Nocturnal cardiovascular recovery deficit audit (Tmin >= 28°C)
- Category classifications based on configuration thresholds
"""

from pathlib import Path
from typing import Union, Dict, Any, Optional
import yaml
import numpy as np
import pandas as pd


def load_thermal_thresholds(config_path: Union[str, Path] = "configs/config.yaml") -> Dict[str, Any]:
    """Load thermal thresholds from config."""
    path = Path(config_path)
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("thermal", {})


# ---------------------------------------------------------------------------
# 1. WBGT & Psychrometrics
# ---------------------------------------------------------------------------

def calculate_natural_wet_bulb(
    temperature_c: Union[float, np.ndarray, pd.Series],
    relative_humidity_pct: Union[float, np.ndarray, pd.Series],
) -> Union[float, np.ndarray, pd.Series]:
    """Stull (2011) psychrometric natural wet-bulb calculation (°C)."""
    t = temperature_c
    rh = np.clip(relative_humidity_pct, 1.0, 100.0)

    tw = (
        t * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(t + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * (rh**1.5) * np.arctan(0.023101 * rh)
        - 4.686035
    )
    if isinstance(temperature_c, (int, float)):
        return float(tw)
    return tw


def calculate_globe_temperature(
    temperature_c: Union[float, np.ndarray, pd.Series],
    solar_radiation_wm2: Union[float, np.ndarray, pd.Series],
    wind_speed_mps: Union[float, np.ndarray, pd.Series],
) -> Union[float, np.ndarray, pd.Series]:
    """Estimate black globe temperature (°C) from solar radiation and wind speed."""
    s = np.maximum(0.0, solar_radiation_wm2)
    v = np.maximum(0.1, wind_speed_mps)
    tg = temperature_c + (0.05 * s) / (v + 0.5)
    if isinstance(temperature_c, (int, float)):
        return float(tg)
    return tg


def calculate_outdoor_wbgt(
    temperature_c: Union[float, np.ndarray, pd.Series],
    relative_humidity_pct: Union[float, np.ndarray, pd.Series],
    wind_speed_mps: Union[float, np.ndarray, pd.Series],
    solar_radiation_wm2: Union[float, np.ndarray, pd.Series],
) -> Union[float, np.ndarray, pd.Series]:
    """Standard outdoor WBGT: 0.7 Tw + 0.2 Tg + 0.1 Ta."""
    tw = calculate_natural_wet_bulb(temperature_c, relative_humidity_pct)
    tg = calculate_globe_temperature(temperature_c, solar_radiation_wm2, wind_speed_mps)
    wbgt = 0.7 * tw + 0.2 * tg + 0.1 * temperature_c
    if isinstance(temperature_c, (int, float)):
        return round(float(wbgt), 2)
    return np.round(wbgt, 2)


def calculate_indoor_wbgt(
    temperature_c: Union[float, np.ndarray, pd.Series],
    relative_humidity_pct: Union[float, np.ndarray, pd.Series],
) -> Union[float, np.ndarray, pd.Series]:
    """Indoor / shaded WBGT: 0.7 Tw + 0.3 Ta."""
    tw = calculate_natural_wet_bulb(temperature_c, relative_humidity_pct)
    wbgt_in = 0.7 * tw + 0.3 * temperature_c
    if isinstance(temperature_c, (int, float)):
        return round(float(wbgt_in), 2)
    return np.round(wbgt_in, 2)


# ---------------------------------------------------------------------------
# 2. NOAA Heat Index
# ---------------------------------------------------------------------------

def calculate_heat_index(
    temperature_c: Union[float, np.ndarray, pd.Series],
    relative_humidity_pct: Union[float, np.ndarray, pd.Series],
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate NOAA Rothfusz regression Heat Index (°C)."""
    is_scalar = isinstance(temperature_c, (int, float))
    tc = np.asarray(temperature_c, dtype=float)
    rh = np.clip(np.asarray(relative_humidity_pct, dtype=float), 0.0, 100.0)

    tf = tc * 9.0 / 5.0 + 32.0
    hi_simple = 0.5 * (tf + 61.0 + ((tf - 68.0) * 1.2) + (rh * 0.094))

    c1, c2, c3 = -42.379, 2.04901523, 10.14333127
    c4, c5, c6 = -0.22475541, -0.00683783, -0.05481717
    c7, c8, c9 = 0.00122874, 0.00085282, -0.00000199

    hi_rothfusz = (
        c1 + c2 * tf + c3 * rh + c4 * tf * rh
        + c5 * (tf**2) + c6 * (rh**2)
        + c7 * (tf**2) * rh + c8 * tf * (rh**2) + c9 * (tf**2) * (rh**2)
    )

    # NOAA adjustments
    low_rh_mask = (rh < 13.0) & (tf >= 80.0) & (tf <= 112.0)
    adj_low = ((13.0 - rh) / 4.0) * np.sqrt(np.maximum(0.0, (17.0 - np.abs(tf - 95.0)) / 17.0))
    hi_rothfusz = np.where(low_rh_mask, hi_rothfusz - adj_low, hi_rothfusz)

    high_rh_mask = (rh > 85.0) & (tf >= 80.0) & (tf <= 87.0)
    adj_high = ((rh - 85.0) / 10.0) * ((87.0 - tf) / 5.0)
    hi_rothfusz = np.where(high_rh_mask, hi_rothfusz + adj_high, hi_rothfusz)

    final_hi_f = np.where(hi_simple >= 80.0, hi_rothfusz, hi_simple)
    final_hi_c = np.round((final_hi_f - 32.0) * 5.0 / 9.0, 2)

    if is_scalar:
        return float(final_hi_c.item())
    return final_hi_c


# ---------------------------------------------------------------------------
# 3. Universal Thermal Climate Index (UTCI)
# ---------------------------------------------------------------------------

def calculate_utci(
    temperature_c: Union[float, np.ndarray, pd.Series],
    relative_humidity_pct: Union[float, np.ndarray, pd.Series],
    wind_speed_mps: Union[float, np.ndarray, pd.Series],
    solar_radiation_wm2: Union[float, np.ndarray, pd.Series],
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate UTCI (°C) based on operational bioclimatic polynomial."""
    is_scalar = isinstance(temperature_c, (int, float))
    ta = np.asarray(temperature_c, dtype=float)
    rh = np.clip(np.asarray(relative_humidity_pct, dtype=float), 1.0, 100.0)
    va = np.maximum(0.5, np.asarray(wind_speed_mps, dtype=float))
    s = np.maximum(0.0, np.asarray(solar_radiation_wm2, dtype=float))

    # Water vapor pressure in kPa (Buck formulation)
    es = 0.61121 * np.exp((18.678 - ta / 234.5) * (ta / (257.14 + ta)))
    va_kpa = es * (rh / 100.0)

    # Bound delta Tmrt to physical range [0, 30] °C
    d_tmrt = np.clip((0.028 * s) / (va**0.3), 0.0, 30.0)

    utci_offset = (
        0.60756702 - 0.02277123 * ta + 8.0647024e-4 * (ta**2)
        - 1.5427137e-4 * (ta**3) - 3.2465198e-6 * (ta**4) + 7.3260285e-8 * (ta**5)
        + 1.3595907 * va - 2.2583652 * (va**0.5) + 0.0880428 * (va**2)
        + 0.516383 * d_tmrt - 0.007623 * (d_tmrt**2) + 0.002811 * ta * d_tmrt
        + 0.283151 * va_kpa - 0.051411 * (va_kpa**2)
    )

    utci = np.round(ta + utci_offset, 2)
    if is_scalar:
        return float(utci.item())
    return utci


# ---------------------------------------------------------------------------
# 4. Categories & Nocturnal Recovery Deficit
# ---------------------------------------------------------------------------

def evaluate_nocturnal_recovery(
    min_night_temp_c: float,
    critical_threshold_c: float = 28.0,
) -> Dict[str, Union[bool, float, str]]:
    """Evaluate whether nocturnal cardiovascular recovery threshold is breached (Tmin >= 28°C)."""
    is_breached = bool(min_night_temp_c >= critical_threshold_c)
    deficit = max(0.0, float(min_night_temp_c - critical_threshold_c))
    return {
        "is_recovery_deficit": is_breached,
        "critical_threshold_c": critical_threshold_c,
        "min_night_temp_c": min_night_temp_c,
        "recovery_deficit_degrees_c": round(deficit, 2),
        "status": "CRITICAL_DEFICIT" if is_breached else "SUFFICIENT_RECOVERY",
    }


def categorize_wbgt(wbgt_c: float) -> str:
    """Classify WBGT into standard ISO/IMD risk categories."""
    if np.isnan(wbgt_c):
        return "UNKNOWN"
    if wbgt_c >= 34.0:
        return "Extreme Hazard"
    elif wbgt_c >= 32.0:
        return "Severe Risk"
    elif wbgt_c >= 30.0:
        return "High Risk"
    elif wbgt_c >= 28.0:
        return "Caution"
    return "Normal / Low"


def categorize_heat_index(hi_c: float) -> str:
    """Classify NOAA Heat Index into danger categories."""
    if np.isnan(hi_c):
        return "UNKNOWN"
    if hi_c >= 52.0:
        return "Extreme Danger"
    elif hi_c >= 40.0:
        return "Danger"
    elif hi_c >= 32.0:
        return "Extreme Caution"
    elif hi_c >= 27.0:
        return "Caution"
    return "Normal"
