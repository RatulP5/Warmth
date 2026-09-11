"""
config.py
─────────
All constants for the environment module in one place.
Change paths / thresholds here; no other file needs editing.
"""

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent.parent   # heatwave_ml/
RAW_DIR       = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

GEOJSON_PATH = str(RAW_DIR  / "kolkata_wards.geojson")
OUTPUT_PATH  = str(PROCESSED_DIR / "03_ward_env_features.parquet")

# ── Projections ───────────────────────────────────────────────────────────────
WGS84_EPSG        = 4326
KOLKATA_UTM_EPSG  = 32645   # UTM Zone 45N  (metres)

# ── Monthly analysis windows (Mar-Jun 2024) ───────────────────────────────────
# Format: (YYYY-MM-DD, YYYY-MM-DD) inclusive
MONTHLY_WINDOWS = [
    ("2024-03-01", "2024-03-31"),
    ("2024-04-01", "2024-04-30"),
    ("2024-05-01", "2024-05-31"),
    ("2024-06-01", "2024-06-30"),
]

# ── Satellite query parameters ────────────────────────────────────────────────
# Maximum scene-level cloud cover (%) for Sentinel-2 scene search
MAX_CLOUD_COVER = 15

# Minimum fraction of non-NaN pixels for a scene to be included in compositing
# (scenes below this threshold are skipped as too cloud-contaminated)
MIN_VALID_PIXEL_FRACTION = 0.30

# ── Thresholds for land-cover classification ──────────────────────────────────
NDVI_VEG_THRESHOLD   = 0.25   # NDVI > threshold  →  vegetated pixel
NDWI_WATER_THRESHOLD = 0.30   # NDWI > threshold  →  open-water pixel

# ── Landsat Collection 2 Level-2 Surface Temperature (ST_B10 / lwir11) ───────
# Conversion:  LST_kelvin  = raw_digital_number * LST_SCALE + LST_OFFSET
#              LST_celsius = LST_kelvin + LST_K_TO_C
LST_SCALE  = 0.00341802
LST_OFFSET = 149.0       # Kelvin additive offset
LST_K_TO_C = -273.15     # Kelvin to Celsius

# ── Planetary Computer STAC endpoint ─────────────────────────────────────────
PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
