import numpy as np
import pandas as pd


def calculate_relative_humidity(ta: pd.Series, td: pd.Series) -> pd.Series:
    es = 6.112 * np.exp((17.67 * ta) / (ta + 243.5))
    ea = 6.112 * np.exp((17.67 * td) / (td + 243.5))
    rh = (ea / es) * 100
    return pd.Series(np.minimum(rh, 100.0))


def calculate_wet_bulb_stull(ta: pd.Series, rh: pd.Series) -> pd.Series:
    tw = (
        ta * np.arctan(0.151977 * np.sqrt(rh + 8.313659))
        + np.arctan(ta + rh)
        - np.arctan(rh - 1.676331)
        + 0.00391838 * np.power(rh, 1.5) * np.arctan(0.023101 * rh)
        - 4.686035
    )
    return tw


def calculate_globe_temperature(
    ta: pd.Series, solar_rad_w_m2: pd.Series, wind_speed: pd.Series
) -> pd.Series:
    wind_safe = wind_speed.replace(0, 0.1)
    return ta + (solar_rad_w_m2 / (0.15 * wind_safe + 1.0)) * 0.025


def extract_census_worker_data(census_csv_path: str) -> pd.DataFrame:
    """
    Extracts ONLY the Outdoor Worker Percentage from the 2011 Census.
    Leaves density and elderly calculations to the WorldPop GEE data.
    """
    raw_census = pd.read_csv(census_csv_path, low_memory=False)
    ward_census = raw_census[raw_census["Level"] == "WARD"].copy()
    ward_census["WARD"] = ward_census["Ward"].astype(str)

    # Calculate Vulnerable Outdoor Worker Percentage
    vulnerable_workers = (
        ward_census["MARGWORK_P"] + ward_census["MAIN_AL_P"] + ward_census["MAIN_OT_P"]
    )
    ward_census["Outdoor_Worker_Percent"] = (vulnerable_workers / ward_census["TOT_P"]) * 100

    return ward_census[["WARD", "Outdoor_Worker_Percent"]].copy()


def calculate_human_stress_index(wbgt, density, elderly, workers, ndvi, ndbi):
    """Fuses physical heat risk with normalized demographic vulnerability."""
    norm_density = density / 45000.0
    norm_elderly = elderly / 15.0
    norm_workers = workers / 40.0

    env_modifier = (ndbi * 0.5) - (ndvi * 0.5)
    vulnerability_score = (
        (norm_density * 0.2) + (norm_elderly * 0.3) + (norm_workers * 0.5) + env_modifier
    )

    risk_multiplier = np.clip(1.0 + vulnerability_score, 1.0, 2.0)
    return wbgt * risk_multiplier


def process_master_pipeline(gee_timeseries_path: str, census_path: str, output_path: str):
    """
    Executes the full pipeline: Cleans weather, calculates WBGT, merges Census,
    computes HSI, and drops raw unscaled population counts.
    """
    # 1. Load GEE Data (Assumes WorldPop metrics are already included from extraction)
    df = pd.read_csv(gee_timeseries_path)
    df["WARD"] = df["WARD"].astype(str)

    # 2. Time-Aware Weather Imputation
    era5_columns = [
        "dewpoint_temperature_2m",
        "surface_solar_radiation_downwards",
        "temperature_2m",
        "u_component_of_wind_10m",
        "v_component_of_wind_10m",
        "Ta_Celsius",
        "Td_Celsius",
    ]
    df[era5_columns] = df.groupby("date")[era5_columns].transform(lambda x: x.fillna(x.mean()))

    # 3. Physics & WBGT Calculations
    df["wind_speed_m_s"] = np.sqrt(
        df["u_component_of_wind_10m"] ** 2 + df["v_component_of_wind_10m"] ** 2
    )
    df["solar_rad_W_m2"] = df["surface_solar_radiation_downwards"] / 3600.0
    df["RH_percent"] = calculate_relative_humidity(df["Ta_Celsius"], df["Td_Celsius"])

    df["UHI_Offset"] = (df["LST_Celsius"] - df["Ta_Celsius"]) * 0.15
    df["Localized_Ta"] = df["Ta_Celsius"] + df["UHI_Offset"]

    df["Tw_Celsius"] = calculate_wet_bulb_stull(df["Localized_Ta"], df["RH_percent"])
    df["Tg_Celsius"] = calculate_globe_temperature(
        df["Localized_Ta"], df["solar_rad_W_m2"], df["wind_speed_m_s"]
    )
    df["WBGT_Celsius"] = (
        (0.7 * df["Tw_Celsius"]) + (0.2 * df["Tg_Celsius"]) + (0.1 * df["Localized_Ta"])
    )

    # 4. Merge Census Worker Data
    df_census = extract_census_worker_data(census_path)
    df_fused = pd.merge(df, df_census, on="WARD", how="left")
    df_fused["Outdoor_Worker_Percent"] = df_fused["Outdoor_Worker_Percent"].fillna(
        df_fused["Outdoor_Worker_Percent"].median()
    )

    # 5. Calculate Final Human Stress Index
    # Uses WorldPop for density/elderly and Census for workers
    df_fused["Human_Stress_Index"] = calculate_human_stress_index(
        df_fused["WBGT_Celsius"],
        df_fused["Pop_Density_per_sqkm"],
        df_fused["Elderly_Percent"],
        df_fused["Outdoor_Worker_Percent"],
        df_fused["NDVI"],
        df_fused["NDBI"],
    )

    # 6. Strict Column Formatting for the TFT
    # Drop raw population/elderly counts to prevent neural network scaling issues
    columns_to_drop = [
        col for col in df_fused.columns if col.lower() in ["population", "tot_p", "elderly_pop"]
    ]
    df_final = df_fused.drop(columns=columns_to_drop, errors="ignore")

    # Ensure sequential time index exists
    if "time_idx" not in df_final.columns:
        date_mapping = {date: idx for idx, date in enumerate(sorted(df_final["date"].unique()))}
        df_final["time_idx"] = df_final["date"].map(date_mapping)

    df_final = df_final.round(3)
    df_final.to_csv(output_path, index=False)
    print(f"Master processing complete. Ready for TFT. Output saved to: {output_path}")

    return df_final


if __name__ == "__main__":
    # The CSV from Google Earth Engine (contains ERA5, Landsat, and WorldPop)
    GEE_INPUT = "./data/kolkata_timeseries_heat_metrics.csv"
    # The official 2011 Census CSV
    CENSUS_INPUT = "DDW_PCA1916_2011_MDDS with UI.csv"
    # The final output to feed PyTorch Forecasting
    OUTPUT_FILE = "./data/kolkata_tft_training_ready.csv"

    process_master_pipeline(GEE_INPUT, CENSUS_INPUT, OUTPUT_FILE)
