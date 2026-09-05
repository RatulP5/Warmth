"""Unified Master Command-Line Interface for Heatwave Early Warning Platform.

Usage:
  python pipeline.py run-all --demo      # Run complete end-to-end pipeline (default)
  python pipeline.py spatial --demo      # Extract satellite raster & OSM vector features
  python pipeline.py dataset --demo      # Assemble and partition training dataset
  python pipeline.py train --demo        # Train LightGBM & Multi-Horizon models
  python pipeline.py forecast --demo     # Generate real-time 5-day risk forecast
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd

from data.demo.generate_demo_data import generate_all_demo_data
from validation.validator import audit_weather_dataframe, audit_health_dataframe, save_quality_report
from geospatial.boundaries import WardBoundaryManager
from geospatial.spatial_features import RasterFeatureExtractor, VectorFeatureExtractor
from ingestion.health_and_census import CensusDataLoader
from features.feature_pipeline import compute_morphological_hvi
from datasets.dataset_builder import DatasetBuilder
from training.trainer import train_baseline_pipeline, train_temporal_pipeline
from inference.forecaster import HealthRiskForecaster


def run_spatial(city_name: str = "Kolkata", demo_mode: bool = True) -> pd.DataFrame:
    print(f"[*] Extracting ward spatial features for {city_name} (demo={demo_mode})...")
    boundary_mgr = WardBoundaryManager()
    gdf_wards = boundary_mgr.load_ward_boundaries(city_name=city_name, demo_mode=demo_mode)
    raster_ext = RasterFeatureExtractor()
    vector_ext = VectorFeatureExtractor()
    census_loader = CensusDataLoader()

    ward_ids = list(gdf_wards["ward_id"])
    df_census = census_loader.load_ward_demographics(demo_mode=demo_mode, ward_ids=ward_ids)

    records = []
    for _, w in gdf_wards.iterrows():
        w_id = w["ward_id"]
        row = dict(raster_ext.extract_ward_raster_features(w_id, demo_mode=demo_mode))
        row.update(vector_ext.extract_ward_vector_features(w_id, w["lat"], w["lon"], area_m2=w["area_m2"], demo_mode=demo_mode))

        demo_match = df_census[df_census["ward_id"] == w_id]
        if not demo_match.empty:
            d_row = demo_match.iloc[0]
            for col in ["population_density", "elderly_percentage", "outdoor_worker_density", "slum_percentage"]:
                row[col] = float(d_row[col])

        row["hvi_score"] = compute_morphological_hvi(
            tin_roofs=row["tin_roofs_count"],
            construction_sites=row["construction_site_count"],
            total_buildings=row["building_count"],
            cooling_buffers=row["cooling_buffers_count"],
        )
        records.append(row)

    df_spatial = pd.DataFrame(records)
    out_file = Path("data/features/spatial_features.parquet")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df_spatial.to_parquet(out_file, index=False)
    print(f"[+] Spatial features written to {out_file} ({len(df_spatial)} wards)")
    return df_spatial


def run_dataset(demo_mode: bool = True) -> None:
    print(f"[*] Building training datasets (demo={demo_mode})...")
    weather_path = "data/demo/weather_historical.parquet"
    spatial_path = "data/features/spatial_features.parquet"
    health_path = "data/demo/health.parquet"

    if not Path(spatial_path).exists():
        spatial_path = "data/demo/spatial_features.parquet"

    df_weather = pd.read_parquet(weather_path)
    df_spatial = pd.read_parquet(spatial_path)
    df_health = pd.read_parquet(health_path) if Path(health_path).exists() else None

    builder = DatasetBuilder(output_dir="data/features")
    res = builder.build_and_save(df_weather, df_spatial, df_health)
    print(f"[+] Dataset saved to data/features: Train={res['train_rows']} | Val={res['val_rows']} | Test={res['test_rows']}")


def run_train(demo_mode: bool = True) -> None:
    print(f"[*] Training baseline and multi-horizon models (demo={demo_mode})...")
    base_res = train_baseline_pipeline()
    print(f"[+] LightGBM Baseline Test MAE: {base_res['test_metrics']['MAE']} | Poisson Deviance: {base_res['test_metrics']['poisson_deviance']}")
    print(f"[+] Conformal 80% coverage: {base_res['uncertainty_audit']['empirical_coverage']} (margin: ±{base_res['uncertainty_audit']['conformal_margin']})")

    tft_res = train_temporal_pipeline()
    print(f"[+] Multi-Horizon Model saved to {tft_res['artifact_path']}")
    for day, metrics in tft_res["horizon_metrics"].items():
        print(f"    {day} -> MAE: {metrics['MAE']} | RMSE: {metrics['RMSE']}")


def run_forecast(demo_mode: bool = True) -> None:
    print(f"[*] Running 5-day predictive early warning forecast (demo={demo_mode})...")
    spatial_path = "data/features/spatial_features.parquet"
    if not Path(spatial_path).exists():
        spatial_path = "data/demo/spatial_features.parquet"

    df_fc = pd.read_parquet("data/demo/weather_forecast.parquet")
    df_spatial = pd.read_parquet(spatial_path)
    gdf_wards = gpd.read_file("data/demo/wards.geojson") if Path("data/demo/wards.geojson").exists() else None

    forecaster = HealthRiskForecaster(output_dir="data/predictions")
    results = forecaster.generate_5day_forecast(df_fc, df_spatial, gdf_wards)
    print(f"[+] Forecast complete! Produced {len(results)} ward-day projections in data/predictions/")
    for r in results[:3]:
        print(f"[{r['ward_id']}] {r['forecast_date']} -> Status: {r['risk_tier']} (Surge: +{r['health_risk']['hospitalization_surge_pct']}%)")
        print(f"    Thermal: Peak WBGT {r['thermal_stress']['peak_wbgt_c']}°C | Night Min {r['thermal_stress']['min_night_temp_c']}°C")
        if r["recommended_actions"]:
            print(f"    Action: {r['recommended_actions'][0]}")


def run_all(demo_mode: bool = True) -> None:
    print("================================================================================")
    print("   EXTREME HEATWAVE EARLY WARNING AND HUMAN THERMAL STRESS INDEX PLATFORM")
    print("   Consolidated Modular Python Pipeline")
    print("================================================================================")
    print(f"Mode: {'OFFLINE DEMO' if demo_mode else 'LIVE API'}\n")

    if demo_mode:
        print("[Step 1/5] Ingesting demo data...")
        generate_all_demo_data(output_dir="data/demo")
        print("[+] Demo datasets ready.\n")

    print("[Step 2/5] Running data quality audits...")
    w_report = audit_weather_dataframe(pd.read_parquet("data/demo/weather_historical.parquet"))
    h_report = audit_health_dataframe(pd.read_parquet("data/demo/health.parquet"))
    save_quality_report([w_report, h_report])
    print("[+] Quality report saved.\n")

    print("[Step 3/5] Extracting spatial features...")
    run_spatial(demo_mode=demo_mode)
    print()

    print("[Step 4/5] Building dataset and training models...")
    run_dataset(demo_mode=demo_mode)
    run_train(demo_mode=demo_mode)
    print()

    print("[Step 5/5] Generating 5-day predictive early warning forecast...")
    run_forecast(demo_mode=demo_mode)
    print("\n================================================================================")
    print("   EXECUTION SUCCESSFUL")
    print("================================================================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified Heatwave Early Warning Pipeline.")
    parser.add_argument("command", nargs="?", default="run-all", choices=["spatial", "dataset", "train", "forecast", "run-all"], help="Subcommand to execute")
    parser.add_argument("--demo", action="store_true", default=True, help="Run in demo mode")
    args = parser.parse_args()

    cmd = args.command
    if cmd == "spatial":
        run_spatial(demo_mode=args.demo)
    elif cmd == "dataset":
        run_dataset(demo_mode=args.demo)
    elif cmd == "train":
        run_train(demo_mode=args.demo)
    elif cmd == "forecast":
        run_forecast(demo_mode=args.demo)
    else:
        run_all(demo_mode=args.demo)
