"""
heatwave_ml/exposure/pipeline.py
────────────────────────────────
Assembles the complete Step 4 Human Exposure dataset by combining:
  1. Daily thermal metrics (WBGT, UTCI, persistence, cumulative 72h stress)
  2. Monthly environmental morphology from Step 3 (LST, NDVI, builtup, roads)
  3. Official Census demographics & outdoor worker exposure proxies

Output:
  heatwave_ml/data/processed/04_ward_exposure_features.parquet
"""

import argparse
from pathlib import Path
import pandas as pd
import numpy as np

try:
    from . import config as cfg
    from .census import CensusExposureLoader
    from .thermal_exposure import ThermalExposureAggregator
except ImportError:
    import config as cfg
    from census import CensusExposureLoader
    from thermal_exposure import ThermalExposureAggregator


class ExposurePipeline:
    """
    Orchestrates ingestion, aggregation, and synthesis of human exposure features.
    """

    def __init__(
        self,
        weather_path: str = cfg.WEATHER_PROCESSED_PATH,
        env_path: str = cfg.ENVIRONMENT_PATH,
        census_path: str = cfg.CENSUS_PATH,
        output_path: str = cfg.OUTPUT_PATH,
    ):
        self.weather_path = weather_path
        self.env_path = env_path
        self.census_path = census_path
        self.output_path = output_path
        self.census_loader = CensusExposureLoader(census_path=census_path)
        self.thermal_aggregator = ThermalExposureAggregator(weather_path=weather_path)

    def run(self, ward_ids: list[str] | None = None) -> pd.DataFrame:
        """
        Execute the exposure pipeline.
        """
        print("\n=== [Step 4] Human Exposure Pipeline Starting ===")

        # 1. Load census demographics & outdoor labor proxies
        print("  [1/3] Loading Census 2011 demographic exposure...")
        census_df = self.census_loader.load()
        if ward_ids:
            census_df = census_df[census_df["ward_id"].isin(ward_ids)].copy()
        print(f"        Loaded {len(census_df)} ward profiles.")

        # 2. Aggregate weather & thermal exposure metrics
        print("  [2/3] Aggregating daily thermal stress metrics (WBGT, UTCI, persistence)...")
        thermal_df = self.thermal_aggregator.process(ward_ids=ward_ids)
        print(f"        Generated {len(thermal_df)} ward-day observations.")

        # 3. Load Step 3 Environmental Features
        print("  [3/3] Merging environmental context from Step 3...")
        env_file = Path(self.env_path)
        if not env_file.exists():
            test_env = Path(cfg.ENVIRONMENT_TEST_PATH)
            if test_env.exists():
                print(f"        Notice: '{self.env_path}' not found, falling back to '{test_env}'")
                env_file = test_env

        if env_file.exists():
            env_df = pd.read_parquet(env_file)
            print(f"        Loaded {len(env_df)} environmental records from {env_file.name}.")
        else:
            print("        Notice: Environmental parquet not yet generated. Setting spatial env features to NaN.")
            env_df = pd.DataFrame(columns=[
                "ward_id", "year_month", "lst_mean", "lst_p90",
                "ndvi_mean", "vegetation_fraction", "builtup_fraction",
                "road_density_m_km2", "data_quality"
            ])

        # Merge thermal with census static features on ward_id
        merged = pd.merge(thermal_df, census_df, on="ward_id", how="left")

        # Merge with monthly environmental data on (ward_id, year_month)
        merged["year_month"] = merged["date"].dt.strftime("%Y-%m")

        env_cols = [
            "ward_id", "year_month", "lst_mean", "lst_p90",
            "ndvi_mean", "vegetation_fraction", "builtup_fraction",
            "road_density_m_km2", "data_quality"
        ]
        available_env_cols = [c for c in env_cols if c in env_df.columns]
        if not env_df.empty and available_env_cols:
            merged = pd.merge(
                merged,
                env_df[available_env_cols],
                on=["ward_id", "year_month"],
                how="left",
            )
        else:
            for col in ["lst_mean", "lst_p90", "ndvi_mean", "vegetation_fraction", "builtup_fraction", "road_density_m_km2"]:
                merged[col] = np.nan
            merged["data_quality"] = "env_pending"

        # Organize final columns
        final_cols = [
            "ward_id", "ward_name", "date", "year_month",
            # Thermal Exposure
            "temp_daily_max", "temp_daily_mean",
            "wbgt_daily_max", "wbgt_daily_mean",
            "utci_daily_max", "utci_daily_mean",
            "nocturnal_wbgt_mean", "nocturnal_temp_mean",
            "tropical_night_flag", "tropical_night_count_3d",
            "heatwave_persistence_days", "cumulative_thermal_stress_72h",
            "relative_humidity_mean", "solar_radiation_sum",
            # Environmental Features
            "lst_mean", "lst_p90", "ndvi_mean",
            "vegetation_fraction", "builtup_fraction", "road_density_m_km2",
            # Demographic Exposure
            "population", "ward_area_km2", "population_density_km2",
            "outdoor_labor_population", "outdoor_labor_fraction",
            "outdoor_exposure_score",
            # Quality & Metadata
            "data_quality", "is_proxy", "source", "source_year"
        ]

        out_cols = [c for c in final_cols if c in merged.columns]
        merged = merged[out_cols].copy()

        # Save to parquet
        out_path = Path(self.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(out_path, index=False)

        print(f"\n[ExposurePipeline] Output successfully written to: {out_path}")
        print(f"                   Total Records : {len(merged)}")
        print(f"                   Unique Wards  : {merged['ward_id'].nunique()}")
        print(f"                   Date Range    : {merged['date'].min()} to {merged['date'].max()}")
        return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Step 4 Human Exposure Pipeline.")
    parser.add_argument("--ward", nargs="*", default=None, help="Specific ward IDs to process.")
    parser.add_argument("--output", default=cfg.OUTPUT_PATH, help="Output Parquet path.")
    args = parser.parse_args()

    pipeline = ExposurePipeline(output_path=args.output)
    pipeline.run(ward_ids=args.ward)
