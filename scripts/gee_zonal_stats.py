import os

import ee
import geopandas as gpd
import pandas as pd


def initialize_gee_session():
    """Authenticates and initializes Google Earth Engine."""
    project_id = os.getenv("EE_PROJECT_ID", "sih-heatwave-2026")
    try:
        ee.Initialize(project=project_id)
    except ee.EEException:
        ee.Authenticate()
        ee.Initialize(project=project_id)


def load_kolkata_wards_from_geojson(geojson_path: str):
    """Loads Kolkata ward GeoJSON and converts it into an ee.FeatureCollection."""
    gdf = gpd.read_file(geojson_path)

    if "WARD" not in gdf.columns:
        raise KeyError("Expected property 'WARD' not found in GeoJSON attributes.")

    features = []
    for _, row in gdf.iterrows():
        properties = {"WARD": str(row["WARD"])}
        for col in gdf.columns:
            if col not in ["geometry", "WARD"]:
                properties[col] = row[col]
        geom = ee.Geometry(row.geometry.__geo_interface__)
        features.append(ee.Feature(geom, properties))

    return ee.FeatureCollection(features)


def compute_timeseries_era5(ward_collection, start_date_str: str, end_date_str: str):
    """
    Computes spatial mean of ERA5-Land parameters for each day in a date range.
    Returns a flattened FeatureCollection representing Ward x Day.
    """
    start_date = ee.Date(start_date_str)
    end_date = ee.Date(end_date_str)

    # Calculate total days to loop over
    num_days = end_date.difference(start_date, "day")

    era5_bands = [
        "temperature_2m",
        "dewpoint_temperature_2m",
        "u_component_of_wind_10m",
        "v_component_of_wind_10m",
        "surface_solar_radiation_downwards",
    ]
    era5_hourly = ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY").select(era5_bands)

    def compute_daily_mean(day_offset):
        """Internal function mapped over the sequence of days."""
        current_day = start_date.advance(day_offset, "day")
        next_day = current_day.advance(1, "day")
        daily_img = era5_hourly.filterDate(current_day, next_day).mean()
        # Tag the image with the date string
        return daily_img.set("date", current_day.format("YYYY-MM-dd"))

    # Generate daily image collection
    days_seq = ee.List.sequence(0, num_days.subtract(1))
    daily_images = ee.ImageCollection(days_seq.map(compute_daily_mean))

    def reduce_ward_stats(img):
        """Zonal statistics for a single daily image."""
        reduced = img.reduceRegions(
            collection=ward_collection, reducer=ee.Reducer.mean(), scale=9000
        )
        img_date = img.get("date")

        # Inject the date into every ward polygon's properties
        def set_date(feature):
            return feature.set("date", img_date)

        return reduced.map(set_date)

    # Flatten the collection of collections into a single tabular format
    timeseries_features = daily_images.map(reduce_ward_stats).flatten()
    return timeseries_features


def compute_landsat_microclimate_baseline(ward_collection, season_start: str, season_end: str):
    """Calculates median LST, NDVI, and NDBI using Landsat 8 and 9 to bypass clouds."""

    def process_landsat_bands(img):
        lst_celsius = (
            img.select("ST_B10")
            .multiply(0.00341802)
            .add(149.0)
            .subtract(273.15)
            .rename("LST_Celsius")
        )
        ndvi = img.normalizedDifference(["SR_B5", "SR_B4"]).rename("NDVI")
        ndbi = img.normalizedDifference(["SR_B6", "SR_B5"]).rename("NDBI")
        return img.addBands([lst_celsius, ndvi, ndbi])

    cloud_filter = ee.Filter.lt("CLOUD_COVER", 30)

    landsat8 = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterDate(season_start, season_end)
        .filterBounds(ward_collection)
        .filter(cloud_filter)
    )
    landsat9 = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterDate(season_start, season_end)
        .filterBounds(ward_collection)
        .filter(cloud_filter)
    )

    merged_landsat = (
        landsat8.merge(landsat9)
        .map(process_landsat_bands)
        .select(["LST_Celsius", "NDVI", "NDBI"])
        .median()
    )

    reduced_features = merged_landsat.reduceRegions(
        collection=ward_collection, reducer=ee.Reducer.mean(), scale=30
    )
    return reduced_features


def compute_worldpop_demographics(ward_collection, target_year: str = "2020"):
    """Calculates ward population density and the percentage aged 60 or older."""
    year_start = f"{target_year}-01-01"
    year_end = f"{int(target_year) + 1}-01-01"

    pop_total = (
        ee.ImageCollection("WorldPop/GP/100m/pop")
        .filter(ee.Filter.eq("country", "IND"))
        .filterDate(year_start, year_end)
        .select("population")
        .first()
    )

    pop_age = (
        ee.ImageCollection("WorldPop/GP/100m/pop_age_sex")
        .filter(ee.Filter.eq("country", "IND"))
        .filterDate(year_start, year_end)
        .first()
    )

    elderly_bands = [
        "M_60",
        "M_65",
        "M_70",
        "M_75",
        "M_80",
        "F_60",
        "F_65",
        "F_70",
        "F_75",
        "F_80",
    ]
    elderly_pop = pop_age.select(elderly_bands).reduce(ee.Reducer.sum()).rename("elderly_pop")
    combined = pop_total.addBands(elderly_pop)

    ward_stats = combined.reduceRegions(
        collection=ward_collection,
        reducer=ee.Reducer.sum(),
        scale=100,
    )

    def calculate_metrics(feature):
        area_sqkm = feature.geometry().area().divide(1e6)
        total_pop = ee.Number(feature.get("population"))
        elderly_count = ee.Number(feature.get("elderly_pop"))
        total_pop = total_pop.max(1)
        elderly_count = elderly_count.max(0)

        return feature.set(
            {
                "Area_sqkm": area_sqkm,
                "Pop_Density_per_sqkm": total_pop.divide(area_sqkm),
                "Elderly_Percent": elderly_count.divide(total_pop).multiply(100),
            }
        )

    return ward_stats.map(calculate_metrics)


def collection_to_df(feature_collection):
    """Converts computed GEE collection to a local pandas DataFrame."""
    computed = feature_collection.getInfo()["features"]
    records = [feat["properties"] for feat in computed]
    return pd.DataFrame(records)


def run_kolkata_timeseries_pipeline(
    geojson_path: str,
    ts_start_date: str,
    ts_end_date: str,
    summer_start: str,
    summer_end: str,
    output_csv_path: str,
):
    """Executes the extraction and downscaling pipeline for Kolkata wards."""
    print("1. Authenticating GEE session...")
    initialize_gee_session()

    print(f"2. Loading Kolkata polygons from: {geojson_path}")
    wards = load_kolkata_wards_from_geojson(geojson_path)

    print(f"3. Computing ERA5 macro-climate time-series ({ts_start_date} to {ts_end_date})...")
    era5_stats = compute_timeseries_era5(wards, ts_start_date, ts_end_date)
    era5_df = collection_to_df(era5_stats)

    print(f"4. Computing Landsat 30m static baselines ({summer_start} to {summer_end})...")
    lst_stats = compute_landsat_microclimate_baseline(wards, summer_start, summer_end)
    lst_df = collection_to_df(lst_stats)

    print("5. Computing WorldPop demographic vulnerability metrics...")
    demographic_stats = compute_worldpop_demographics(wards)
    demographic_df = collection_to_df(demographic_stats)

    print("6. Fusing weather, microclimate, and demographic features...")
    fused_df = pd.merge(
        era5_df, lst_df[["WARD", "LST_Celsius", "NDVI", "NDBI"]], on="WARD", how="inner"
    )
    fused_df = pd.merge(
        fused_df,
        demographic_df[
            [
                "WARD",
                "population",
                "elderly_pop",
                "Area_sqkm",
                "Pop_Density_per_sqkm",
                "Elderly_Percent",
            ]
        ],
        on="WARD",
        how="inner",
    )

    # Standardize unit conversions from raw ERA5 (Kelvin -> Celsius)
    if "temperature_2m" in fused_df.columns:
        fused_df["Ta_Celsius"] = fused_df["temperature_2m"] - 273.15
    if "dewpoint_temperature_2m" in fused_df.columns:
        fused_df["Td_Celsius"] = fused_df["dewpoint_temperature_2m"] - 273.15

    # 6. Generate the PyTorch Forecasting 'time_idx'
    print("7. Formatting sequence constraints (time_idx)...")
    fused_df = fused_df.sort_values(by=["WARD", "date"]).reset_index(drop=True)
    date_mapping = {date: idx for idx, date in enumerate(sorted(fused_df["date"].unique()))}
    fused_df["time_idx"] = fused_df["date"].map(date_mapping)

    fused_df.to_csv(output_csv_path, index=False)
    print(f"Pipeline complete. Time-series dataset saved to: {output_csv_path}")
    return fused_df


if __name__ == "__main__":
    GEOJSON_INPUT = "kolkata.geojson"

    # Extract 30 days of dynamic historical data for the time series
    TS_START = "2024-04-01"
    TS_END = "2024-05-01"

    # 3-year baseline for clear Landsat shots
    SEASON_START = "2021-03-01"
    SEASON_END = "2024-05-31"

    OUTPUT_FILE = "./data/kolkata_timeseries_heat_metrics.csv"

    run_kolkata_timeseries_pipeline(
        GEOJSON_INPUT, TS_START, TS_END, SEASON_START, SEASON_END, OUTPUT_FILE
    )
