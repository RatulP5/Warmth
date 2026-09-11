"""
heatwave_ml/exposure/config.py
──────────────────────────────
Configuration parameters and paths for the Human Exposure module (Step 4).
"""

from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parent.parent
RAW_DIR       = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Source datasets
WEATHER_PROCESSED_PATH = str(PROCESSED_DIR / "kolkata_processed_weather_features.parquet")
ENVIRONMENT_PATH       = str(PROCESSED_DIR / "03_ward_env_features.parquet")
ENVIRONMENT_TEST_PATH  = str(PROCESSED_DIR / "03_ward_env_features_test.parquet")
GEOJSON_PATH           = str(RAW_DIR / "kolkata_wards.geojson")
CENSUS_PATH            = "d:/Warmth/kolkata/data/DDW_PCA1916_2011_MDDS with UI.xlsx"

# Output destination
OUTPUT_PATH = str(PROCESSED_DIR / "04_ward_exposure_features.parquet")

# Spatial reference systems
WGS84_EPSG       = 4326
KOLKATA_UTM_EPSG = 32645

# Thresholds for thermal exposure metrics
WBGT_HEATWAVE_THRESHOLD = 32.0    # degC, standard threshold for extreme thermal risk
WBGT_STRESS_BASE        = 28.0    # degC base for cumulative degree-hours calculation
TEMP_HEATWAVE_THRESHOLD = 37.0    # degC air temperature threshold
