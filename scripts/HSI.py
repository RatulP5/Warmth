import numpy as np
import pandas as pd


def generate_mock_demographics(wards_list: list) -> pd.DataFrame:
    """
    Generates mock census data for the given wards.
    """
    np.random.seed(42)
    return pd.DataFrame(
        {
            "WARD": wards_list,
            "Pop_Density_per_sqkm": np.random.randint(15000, 45000, size=len(wards_list)),
            "Elderly_Percent": np.random.uniform(5.0, 15.0, size=len(wards_list)),
            "Outdoor_Worker_Percent": np.random.uniform(10.0, 40.0, size=len(wards_list)),
        }
    )


def calculate_human_stress_index(wbgt, density, elderly, workers, ndvi, ndbi):
    """
    Fuses physical heat risk with demographic and structural vulnerability.
    """
    # 1. Normalize demographic risk factors
    norm_density = density / 45000.0
    norm_elderly = elderly / 15.0
    norm_workers = workers / 40.0

    # 2. Apply environmental modifiers (NDBI traps heat, NDVI provides relief)
    env_modifier = (ndbi * 0.5) - (ndvi * 0.5)

    # 3. Calculate compound vulnerability (Weights prioritize outdoor workers)
    vulnerability_score = (
        (norm_density * 0.2) + (norm_elderly * 0.3) + (norm_workers * 0.5) + env_modifier
    )

    # 4. Scale the multiplier (Prevents the index from dropping below the baseline weather)
    risk_multiplier = np.clip(1.0 + vulnerability_score, 1.0, 2.0)

    return wbgt * risk_multiplier


def merge_and_compute_hsi(wbgt_csv_path: str, output_csv_path: str):
    """
    Master function to merge time-series weather with census data and calculate the HSI.
    """
    df_weather = pd.read_csv(wbgt_csv_path)

    # Generate static demographics for the unique wards
    df_census = generate_mock_demographics(df_weather["WARD"].unique().tolist())

    # Merge on the WARD join key
    df_fused = pd.merge(df_weather, df_census, on="WARD", how="left")

    # Compute the final Human Stress Index
    df_fused["Human_Stress_Index"] = calculate_human_stress_index(
        df_fused["WBGT_Celsius"],
        df_fused["Pop_Density_per_sqkm"],
        df_fused["Elderly_Percent"],
        df_fused["Outdoor_Worker_Percent"],
        df_fused["NDVI"],
        df_fused["NDBI"],
    )

    df_fused = df_fused.round(3)
    df_fused.to_csv(output_csv_path, index=False)
    print(f"Human Stress Index successfully computed. Output saved to: {output_csv_path}")

    return df_fused


if __name__ == "__main__":
    INPUT_FILE = "./data/kolkata_timeseries_wbgt_final.csv"
    OUTPUT_FILE = "./data/kolkata_final_hsi_dashboard.csv"

    merge_and_compute_hsi(INPUT_FILE, OUTPUT_FILE)
