"""Unified Demographic Vulnerability and Health Outcome Loaders.

Adheres strictly to epidemiological integrity:
- NEVER converts missing health records into zero deaths (preserved as NaN/None).
- Maintains explicit spatial resolution tags ('ward', 'district', 'city').
- Generates synthetic DLNM-aligned historical distributions for demo mode.
"""

from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class CensusDataLoader:
    """Loader for socio-demographic indicators and subgroup distributions."""

    def load_ward_demographics(
        self,
        filepath: Optional[str] = None,
        demo_mode: bool = False,
        ward_ids: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Load demographic table with verified spatial resolution."""
        if filepath and Path(filepath).exists() and not demo_mode:
            return pd.read_parquet(filepath) if filepath.endswith(".parquet") else pd.read_csv(filepath)

        if not ward_ids:
            ward_ids = ["KOL-DD", "KOL-SL", "KOL-BB", "KOL-BH", "KOL-GH"]

        records = []
        np.random.seed(42)
        for w_id in ward_ids:
            total_pop = int(np.random.uniform(35000, 110000))
            area_km2 = float(np.random.uniform(1.5, 5.0))
            pop_density = round(total_pop / area_km2, 1)
            elderly_pct = round(float(np.random.uniform(7.5, 16.5)), 2)
            children_pct = round(float(np.random.uniform(6.0, 12.0)), 2)
            outdoor_pct = round(float(np.random.uniform(12.0, 32.0)), 2)
            slum_pct = round(float(np.random.uniform(5.0, 42.0)), 2)
            worker_density = round((total_pop * (outdoor_pct / 100.0)) / area_km2, 1)

            records.append({
                "ward_id": w_id,
                "spatial_level": "ward",
                "total_population": total_pop,
                "area_km2": area_km2,
                "population_density": pop_density,
                "elderly_percentage": elderly_pct,
                "children_percentage": children_pct,
                "outdoor_worker_percentage": outdoor_pct,
                "outdoor_worker_density": worker_density,
                "slum_percentage": slum_pct,
                "healthcare_accessibility_score": round(float(np.random.uniform(0.4, 0.95)), 2),
            })
        return pd.DataFrame(records)


class HealthDataLoader:
    """Loader for public health outcome registries (mortality, hospital admissions)."""

    def load_health_records(
        self,
        filepath: Optional[str] = None,
        demo_mode: bool = False,
        ward_ids: Optional[List[str]] = None,
        start_date: str = "2024-03-01",
        end_date: str = "2024-05-31",
        spatial_level: str = "ward",
    ) -> pd.DataFrame:
        """Load daily health records with explicit spatial granularity."""
        if filepath and Path(filepath).exists() and not demo_mode:
            df = pd.read_parquet(filepath) if filepath.endswith(".parquet") else pd.read_csv(filepath)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            return df

        if not ward_ids:
            ward_ids = ["KOL-DD", "KOL-SL", "KOL-BB", "KOL-BH", "KOL-GH"]

        dates = pd.date_range(start=start_date, end=end_date, freq="D").date
        records = []
        np.random.seed(42)

        for w_id in ward_ids:
            baseline_mortality = np.random.uniform(9.0, 14.0)
            baseline_surge = np.random.uniform(40.0, 65.0)

            for d in dates:
                is_heatwave = (5 <= d.month <= 6) and (10 <= d.day <= 22)
                temp_factor = 1.35 if is_heatwave else 1.0

                mortality = int(np.random.poisson(baseline_mortality * temp_factor))
                hosp = int(np.random.poisson(baseline_surge * temp_factor * 1.2))
                heat_stroke = int(np.random.poisson(3.5 * temp_factor)) if is_heatwave else 0

                # Strict Rule: Genuine missing reporting days remain None/NaN (never 0)
                if np.random.rand() < 0.03:
                    mortality = None
                if np.random.rand() < 0.03:
                    hosp = None

                records.append({
                    "spatial_id": w_id,
                    "spatial_level": spatial_level,
                    "date": d,
                    "all_cause_mortality": mortality,
                    "emergency_hospitalizations": hosp,
                    "heat_stroke_cases": heat_stroke,
                    "cardiovascular_admissions": int(hosp * 0.4) if hosp is not None else None,
                })
        return pd.DataFrame(records)
