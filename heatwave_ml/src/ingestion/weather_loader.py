import time
import argparse
from pathlib import Path
import requests
import geopandas as gpd
import pandas as pd
import numpy as np
from pythermalcomfort.models import utci

# =====================================================================
# RESOLVE PROJECT PATHS DYNAMICALLY
# =====================================================================
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
WARD_CACHE_DIR = DATA_RAW_DIR / "ward_cache"

DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
WARD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

GEOJSON_FILE = DATA_RAW_DIR / "kolkata_wards.geojson"
RAW_WEATHER_OUTPUT = DATA_RAW_DIR / "01_ward_mapped_historical_weather.parquet"
PROCESSED_OUTPUT = DATA_PROCESSED_DIR / "kolkata_processed_weather_features.parquet"

# Compact 1-year heat season window (Kolkata peak heatwaves)
START_DATE = "2024-03-01"
END_DATE = "2024-06-30"

HOURLY_VARS = [
    "temperature_2m",
    "dew_point_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "shortwave_radiation",
    "surface_pressure",
    "cloud_cover",
    "precipitation",
    "skin_temperature"
]
HOURLY_PARAM_STR = ",".join(HOURLY_VARS)


def load_ward_geometries(geojson_path: Path = GEOJSON_FILE) -> gpd.GeoDataFrame:
    """Loads and validates ward boundary polygons with proper lat/lon coordinate alignment."""
    if not geojson_path.exists():
        alt_path = BASE_DIR / "kolkata_wards.geojson"
        if alt_path.exists():
            geojson_path = alt_path
        else:
            raise FileNotFoundError(f"Ward boundary file not found at '{geojson_path}'!")

    print(f"Loading KMC Ward Polygons from '{geojson_path.name}'...")
    wards_gdf = gpd.read_file(geojson_path)
    if wards_gdf.crs != "EPSG:4326":
        wards_gdf = wards_gdf.to_crs(epsg=4326)

    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        c = wards_gdf.geometry.centroid

    if c.x.mean() < 50.0 and c.y.mean() > 50.0:
        wards_gdf["centroid_lat"] = c.x
        wards_gdf["centroid_lon"] = c.y
    else:
        wards_gdf["centroid_lat"] = c.y
        wards_gdf["centroid_lon"] = c.x

    print(f"   Wards centroid range: Lat [{wards_gdf['centroid_lat'].min():.3f}, {wards_gdf['centroid_lat'].max():.3f}], "
          f"Lon [{wards_gdf['centroid_lon'].min():.3f}, {wards_gdf['centroid_lon'].max():.3f}]")
    return wards_gdf


def fetch_ward_weather(wards_gdf: gpd.GeoDataFrame, max_wards: int = None, force_api: bool = False) -> pd.DataFrame:
    """
    Assembles weather records for all wards.
    - Uses local cache for already-downloaded wards.
    - If force_api is True: queries Open-Meteo in batched requests with rate limit checks.
    - Default (Safe): Fills remaining wards via geographic nearest neighbor to avoid 429 locks.
    """
    ward_col = next((c for c in wards_gdf.columns if c.lower() in ["ward", "ward_no", "name", "id"]), None)
    target_wards = wards_gdf.head(max_wards) if max_wards else wards_gdf

    raw_records = []
    cached_coords = []
    cached_ids = []
    missing_wards = []

    # 1. Read existing cache
    for idx, row in target_wards.iterrows():
        raw_val = row[ward_col] if ward_col else (idx + 1)
        clean_ward = str(raw_val).strip().replace("\n", "").replace("\r", "")
        ward_id = f"KMC_Ward_{clean_ward}"
        cache_file = WARD_CACHE_DIR / f"{ward_id}.parquet"

        lat = float(row["centroid_lat"])
        lon = float(row["centroid_lon"])

        if cache_file.exists():
            df_cached = pd.read_parquet(cache_file)
            raw_records.append(df_cached)
            cached_coords.append((lat, lon))
            cached_ids.append(ward_id)
        else:
            missing_wards.append((ward_id, lat, lon))

    print(f"\n[01. Ingestion Status]")
    print(f"   Available in cache: {len(raw_records)}/{len(target_wards)} wards")
    print(f"   Missing wards:      {len(missing_wards)}/{len(target_wards)} wards")

    # 2. Fetch missing wards
    if missing_wards:
        if force_api:
            print("   Mode: Querying Open-Meteo API for missing wards...")
            BATCH_SIZE = 30
            for b_start in range(0, len(missing_wards), BATCH_SIZE):
                batch = missing_wards[b_start : b_start + BATCH_SIZE]
                batch_ids = [item[0] for item in batch]
                batch_lats = [round(item[1], 4) for item in batch]
                batch_lons = [round(item[2], 4) for item in batch]

                params = {
                    "latitude": ",".join(map(str, batch_lats)),
                    "longitude": ",".join(map(str, batch_lons)),
                    "start_date": START_DATE,
                    "end_date": END_DATE,
                    "hourly": HOURLY_PARAM_STR,
                    "timezone": "Asia/Kolkata"
                }

                url = "https://archive-api.open-meteo.com/v1/archive"
                print(f"   -> Querying batch [{b_start + 1} to {b_start + len(batch)}] of {len(missing_wards)}...")
                resp = requests.get(url, params=params, timeout=60)

                if resp.status_code != 200:
                    print(f"   [!] API returned HTTP {resp.status_code}. Falling back to spatial neighbor filling for remaining wards.")
                    force_api = False
                    break

                results = resp.json()
                if not isinstance(results, list):
                    results = [results]

                for w_id, data_item in zip(batch_ids, results):
                    hourly = data_item.get("hourly", {})
                    times = hourly.get("time", [])

                    ws = np.array(hourly.get("wind_speed_10m", []), dtype=float)
                    wd_rad = np.radians(np.array(hourly.get("wind_direction_10m", []), dtype=float))
                    u10 = -ws * np.sin(wd_rad)
                    v10 = -ws * np.cos(wd_rad)

                    df_ward = pd.DataFrame({
                        "ward_id": w_id,
                        "timestamp": pd.to_datetime(times),
                        "temperature": data_item.get("temperature_2m", hourly.get("temperature_2m")),
                        "dewpoint": data_item.get("dew_point_2m", hourly.get("dew_point_2m")),
                        "wind_speed": ws,
                        "wind_direction": data_item.get("wind_direction_10m", hourly.get("wind_direction_10m")),
                        "wind_u": u10,
                        "wind_v": v10,
                        "solar_radiation": data_item.get("shortwave_radiation", hourly.get("shortwave_radiation")),
                        "surface_pressure": data_item.get("surface_pressure", hourly.get("surface_pressure")),
                        "cloud_cover": data_item.get("cloud_cover", hourly.get("cloud_cover")),
                        "precipitation": data_item.get("precipitation", hourly.get("precipitation")),
                        "skin_temperature": data_item.get("skin_temperature", hourly.get("skin_temperature"))
                    })

                    df_ward.to_parquet(WARD_CACHE_DIR / f"{w_id}.parquet", index=False)
                    raw_records.append(df_ward)

                time.sleep(2.0)

        # Spatial nearest-neighbor fallback for unretrieved wards
        unfilled = [m for m in missing_wards if not (WARD_CACHE_DIR / f"{m[0]}.parquet").exists()]
        if unfilled:
            print(f"   Applying nearest-neighbor mapping for {len(unfilled)} wards...")
            coord_array = np.array(cached_coords)
            for m_id, m_lat, m_lon in unfilled:
                dists = np.hypot(coord_array[:, 0] - m_lat, coord_array[:, 1] - m_lon)
                nearest_idx = int(np.argmin(dists))
                nearest_id = cached_ids[nearest_idx]

                df_imputed = pd.read_parquet(WARD_CACHE_DIR / f"{nearest_id}.parquet").copy()
                df_imputed["ward_id"] = m_id
                df_imputed.to_parquet(WARD_CACHE_DIR / f"{m_id}.parquet", index=False)
                raw_records.append(df_imputed)

    df_all = pd.concat(raw_records, ignore_index=True)
    df_all.to_parquet(RAW_WEATHER_OUTPUT, index=False)
    print(f"\n[01. Done] Full dataset ready: {len(df_all)} total rows across {len(target_wards)} wards.")
    return df_all


def compute_features(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    Computes derived atmospheric metrics, rigorous biometeorological indices
    (UTCI, outdoor ISO 7243 WBGT, Stefan-Boltzmann Tmrt), and cumulative rolling lags.
    """
    print("\n[02] Computing derived atmospheric quantities (RH, Specific Humidity)...")
    T = df_all["temperature"].to_numpy(dtype=float)
    Td = df_all["dewpoint"].to_numpy(dtype=float)
    P = df_all["surface_pressure"].to_numpy(dtype=float)  # hPa

    # 1. Arden Buck equation for saturation and actual vapor pressure (kPa)
    es_T = 0.61121 * np.exp((18.678 - T / 234.5) * (T / (257.14 + T)))
    e_actual = 0.61121 * np.exp((18.678 - Td / 234.5) * (Td / (257.14 + Td)))

    # Relative Humidity (%)
    rh_arr = np.clip((e_actual / es_T) * 100.0, 0.0, 100.0)
    df_all["relative_humidity"] = rh_arr

    # Specific Humidity q (kg/kg): q = (0.622 * e) / (P_kpa - 0.378 * e)
    P_kpa = P / 10.0
    df_all["specific_humidity"] = (0.622 * e_actual) / np.maximum(P_kpa - 0.378 * e_actual, 0.01)

    print("[03] Computing physics-grounded Tmrt, UTCI, and Outdoor WBGT (ISO 7243)...")
    # 2. Downscale 10m wind speed to pedestrian breathing height (~1.2m)
    # v_ped = v_10m * ln(1.2 / z0) / ln(10 / z0) with urban roughness z0 = 0.05m
    v_ped = df_all["wind_speed"].to_numpy(dtype=float) * (np.log(1.2 / 0.05) / np.log(10.0 / 0.05))
    v_ped = np.clip(v_ped, 0.5, 17.0)  # Bound within pythermalcomfort validity envelope

    # 3. Physics-based Mean Radiant Temperature (Tmrt)
    # Human absorption ~0.7, projected area factor ~0.25, wind convective dissipation
    sol_rad = np.maximum(df_all["solar_radiation"].to_numpy(dtype=float), 0.0)
    delta_tmrt = (0.075 * sol_rad) / (1.0 + 0.3 * np.sqrt(v_ped))
    t_mrt = T + delta_tmrt

    # 4. Universal Thermal Climate Index (UTCI, COST Action 730)
    utci_res = utci(
        tdb=T,
        tr=t_mrt,
        v=v_ped,
        rh=rh_arr
    )
    if isinstance(utci_res, dict):
        utci_vals = utci_res["utci"]
    elif hasattr(utci_res, "utci"):
        utci_vals = utci_res.utci
    else:
        utci_vals = utci_res
    df_all["UTCI"] = np.asarray(utci_vals, dtype=float)

    # 5. Outdoor Natural WBGT (ISO 7243)
    # Stull psychrometric wet-bulb formulation
    Tw_stull = (
        T * np.arctan(0.151977 * np.sqrt(rh_arr + 8.313659))
        + np.arctan(T + rh_arr)
        - np.arctan(rh_arr - 1.676331)
        + 0.00391838 * (rh_arr ** 1.5) * np.arctan(0.023101 * rh_arr)
        - 4.686035
    )
    # Add unshaded solar irradiance loading to natural wet-bulb (T_nw)
    T_nw = Tw_stull + (0.004 * sol_rad)

    # Black globe temperature (Tg) incorporating direct solar gain and wind convective dissipation
    Tg = T + (0.015 * sol_rad) / (1.0 + 0.2 * np.sqrt(v_ped))

    # Standard ISO 7243 outdoor equation: 0.7*T_nw + 0.2*Tg + 0.1*T_air
    df_all["WBGT"] = np.asarray(0.7 * T_nw + 0.2 * Tg + 0.1 * T, dtype=float)

    print("[04] Building rolling lag temporal windows & nighttime metrics...")
    df_all = df_all.sort_values(["ward_id", "timestamp"]).reset_index(drop=True)
    grouped = df_all.groupby("ward_id")

    # WBGT moving windows
    df_all["WBGT_6h_mean"] = grouped["WBGT"].transform(lambda s: s.astype(float).rolling(6, min_periods=1).mean())
    df_all["WBGT_24h_mean"] = grouped["WBGT"].transform(lambda s: s.astype(float).rolling(24, min_periods=1).mean())
    df_all["WBGT_24h_max"] = grouped["WBGT"].transform(lambda s: s.astype(float).rolling(24, min_periods=1).max())
    df_all["WBGT_72h_mean"] = grouped["WBGT"].transform(lambda s: s.astype(float).rolling(72, min_periods=1).mean())
    df_all["WBGT_72h_max"] = grouped["WBGT"].transform(lambda s: s.astype(float).rolling(72, min_periods=1).max())

    # UTCI moving windows
    df_all["UTCI_24h_mean"] = grouped["UTCI"].transform(lambda s: s.astype(float).rolling(24, min_periods=1).mean())
    df_all["UTCI_24h_max"] = grouped["UTCI"].transform(lambda s: s.astype(float).rolling(24, min_periods=1).max())
    df_all["UTCI_72h_mean"] = grouped["UTCI"].transform(lambda s: s.astype(float).rolling(72, min_periods=1).mean())

    # Nighttime stress tracking (hours between 22:00 and 06:00 IST)
    hour = df_all["timestamp"].dt.hour
    is_night = (hour >= 22) | (hour <= 6)
    df_all["is_nighttime"] = is_night
    df_all["tropical_night_failure"] = (df_all["temperature"] > 28.0) & is_night

    # Export complete ML-ready matrix
    df_all.to_parquet(PROCESSED_OUTPUT, index=False)
    print(f"\n[05. Complete] Output features written to:\n    {PROCESSED_OUTPUT}")
    return df_all

def main():
    parser = argparse.ArgumentParser(description="Ingest historical weather and compute heatwave features.")
    parser.add_argument("--max-wards", type=int, default=None, help="Limit number of wards for quick testing")
    parser.add_argument("--use-cached-raw", action="store_true", help="Use previously consolidated raw weather file")
    parser.add_argument("--force-api", action="store_true", help="Attempt API call for missing wards instead of neighbor imputation")
    args = parser.parse_args()

    print("=====================================================================")
    print(" 01. Ward-Mapped Weather & Physics Ingestion Pipeline ")
    print("=====================================================================")

    if args.use_cached_raw and RAW_WEATHER_OUTPUT.exists():
        print(f"Loading cached raw weather data from '{RAW_WEATHER_OUTPUT}'...")
        df_weather = pd.read_parquet(RAW_WEATHER_OUTPUT)
    else:
        wards_gdf = load_ward_geometries()
        df_weather = fetch_ward_weather(wards_gdf, max_wards=args.max_wards, force_api=args.force_api)

    df_features = compute_features(df_weather)
    print("\nPipeline Verification Sample:")
    print(df_features[["ward_id", "timestamp", "temperature", "relative_humidity", "UTCI", "WBGT", "WBGT_72h_max"]].head(10))


if __name__ == "__main__":
    main()