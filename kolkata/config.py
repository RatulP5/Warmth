import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# File paths
GEOJSON_PATH = str(DATA_DIR / "kmc_wards.geojson")
PCA_EXCEL_PATH = str(DATA_DIR / "DDW_PCA1916_2011_MDDS with UI.xlsx")

# Projections
WGS84_EPSG = 4326
KOLKATA_UTM_EPSG = 32645  # UTM Zone 45N for metric calculations in meters / sq. meters