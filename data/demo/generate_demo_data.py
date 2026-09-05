"""Synthetic Demo Dataset Generator.

Generates realistic pilot datasets for Kolkata microclimates to exercise
the entire early warning pipeline offline (--demo mode).
"""

from pathlib import Path
from typing import Dict, Any
import pandas as pd
import geopandas as gpd

from geospatial.boundaries import WardBoundaryManager
from ingestion.weather import HistoricalWeatherClient, WeatherForecastClient
from ingestion.health_and_census import CensusDataLoader, HealthDataLoader
from geospatial.spatial_features import RasterFeatureExtractor, VectorFeatureExtractor
from features.feature_pipeline import compute_morphological_hvi


def generate_all_demo_data(output_dir: str = "data/demo") -> Dict[str, str]:
    """Generate and serialize complete offline demonstration dataset."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Ward Boundaries
    boundary_mgr = WardBoundaryManager()
    gdf_wards = boundary_mgr.create_demo_ward_polygons(city_name="Kolkata")
    wards_file = out_path / "wards.geojson"
    gdf_wards.to_file(wards_file, driver="GeoJSON")

    # 2. Historical Weather
    weather_hist_client = HistoricalWeatherClient()
    weather_records = []
    for _, w in gdf_wards.iterrows():
        df_w = weather_hist_client.fetch_historical(
            ward_id=w["ward_id"],
            lat=w["lat"],
            lon=w["lon"],
            start_date="2024-03-01",
            end_date="2024-05-31",
            demo_mode=True,
        )
        weather_records.append(df_w)
    df_weather_hist = pd.concat(weather_records, ignore_index=True)
    weather_hist_file = out_path / "weather_historical.parquet"
    df_weather_hist.to_parquet(weather_hist_file, index=False)

    # 3. 5-Day Forecast Weather
    weather_fc_client = WeatherForecastClient()
    fc_records = []
    for _, w in gdf_wards.iterrows():
        df_fc = weather_fc_client.fetch_forecast(
            ward_id=w["ward_id"],
            lat=w["lat"],
            lon=w["lon"],
            forecast_days=5,
            demo_mode=True,
        )
        fc_records.append(df_fc)
    df_weather_fc = pd.concat(fc_records, ignore_index=True)
    weather_fc_file = out_path / "weather_forecast.parquet"
    df_weather_fc.to_parquet(weather_fc_file, index=False)

    # 4. Demographics
    census_loader = CensusDataLoader()
    ward_ids = list(gdf_wards["ward_id"])
    df_demographics = census_loader.load_ward_demographics(demo_mode=True, ward_ids=ward_ids)
    census_file = out_path / "census.parquet"
    df_demographics.to_parquet(census_file, index=False)

    # 5. Health Data
    health_loader = HealthDataLoader()
    df_health = health_loader.load_health_records(
        demo_mode=True,
        ward_ids=ward_ids,
        start_date="2024-03-01",
        end_date="2024-05-31",
    )
    health_file = out_path / "health.parquet"
    df_health.to_parquet(health_file, index=False)

    # 6. Spatial Features
    raster_extractor = RasterFeatureExtractor()
    vector_extractor = VectorFeatureExtractor()

    spatial_records = []
    for _, w in gdf_wards.iterrows():
        w_id = w["ward_id"]
        r_feats = raster_extractor.extract_ward_raster_features(w_id, demo_mode=True)
        v_feats = vector_extractor.extract_ward_vector_features(
            w_id, w["lat"], w["lon"], area_m2=w["area_m2"], demo_mode=True
        )
        combined = dict(r_feats)
        combined.update(v_feats)

        demo_row = df_demographics[df_demographics["ward_id"] == w_id].iloc[0]
        for col in ["population_density", "elderly_percentage", "outdoor_worker_density", "slum_percentage"]:
            combined[col] = float(demo_row[col])

        combined["hvi_score"] = compute_morphological_hvi(
            tin_roofs=combined["tin_roofs_count"],
            construction_sites=combined["construction_site_count"],
            total_buildings=combined["building_count"],
            cooling_buffers=combined["cooling_buffers_count"],
        )
        spatial_records.append(combined)

    df_spatial = pd.DataFrame(spatial_records)
    spatial_file = out_path / "spatial_features.parquet"
    df_spatial.to_parquet(spatial_file, index=False)

    return {
        "wards_geojson": str(wards_file),
        "weather_historical": str(weather_hist_file),
        "weather_forecast": str(weather_fc_file),
        "census": str(census_file),
        "health": str(health_file),
        "spatial_features": str(spatial_file),
    }


if __name__ == "__main__":
    generate_all_demo_data()
