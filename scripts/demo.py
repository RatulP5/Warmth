import numpy as np
import pandas as pd


def load_kolkata_census_pca(excel_path: str) -> pd.DataFrame:
    """
    Ingests official Kolkata Census 2011 PCA Excel file, filters to
    the 141 KMC wards, and extracts standardized vulnerability metrics.
    """
    # Read the primary enumeration sheet
    df_raw = pd.read_excel(excel_path, sheet_name="EB-1916")

    # Filter strictly to municipal ward-level summaries
    wards_pca = df_raw[df_raw["Level"] == "WARD"].copy()

    # Standardize join key as string to match GeoJSON / weather pipeline
    wards_pca["WARD"] = wards_pca["Ward"].astype(str)

    # Feature engineering for heat vulnerability
    clean_census = pd.DataFrame(
        {
            "WARD": wards_pca["WARD"],
            "Ward_Name": wards_pca["Name"],
            "Total_Population": wards_pca["TOT_P"],
            "Households": wards_pca["No_HH"],
            "Children_Under_6_Percent": (wards_pca["P_06"] / wards_pca["TOT_P"]) * 100.0,
            "Outdoor_Labor_Percent": (wards_pca["MARGWORK_P"] / wards_pca["TOT_P"]) * 100.0,
            "Vulnerable_Social_Group_Percent": (
                (wards_pca["P_SC"] + wards_pca["P_ST"]) / wards_pca["TOT_P"]
            )
            * 100.0,
        }
    )

    return clean_census


def merge_wbgt_with_real_census(wbgt_csv_path: str, census_excel_path: str, output_csv_path: str):
    """
    Fuses WBGT time-series data with official Census metrics to produce
    the final Human Stress Index dataset.
    """
    df_wbgt = pd.read_csv(wbgt_csv_path)
    df_census = load_kolkata_census_pca(census_excel_path)

    # Ensure join key types match
    df_wbgt["WARD"] = df_wbgt["WARD"].astype(str)

    # Left merge to preserve all time-series rows
    fused_df = pd.merge(df_wbgt, df_census, on="WARD", how="left")

    # Normalize vulnerability factors (0 to 1 scale)
    norm_labor = fused_df["Outdoor_Labor_Percent"] / fused_df["Outdoor_Labor_Percent"].max()
    norm_child = fused_df["Children_Under_6_Percent"] / fused_df["Children_Under_6_Percent"].max()
    norm_social = (
        fused_df["Vulnerable_Social_Group_Percent"]
        / fused_df["Vulnerable_Social_Group_Percent"].max()
    )

    # Environmental modifier from GEE Landsat layers
    env_modifier = (fused_df["NDBI"] * 0.5) - (fused_df["NDVI"] * 0.5)

    # Compound vulnerability multiplier (scaled between 1.0 and 2.0)
    vulnerability_score = (
        (norm_labor * 0.4) + (norm_child * 0.3) + (norm_social * 0.3) + env_modifier
    )
    risk_multiplier = np.clip(1.0 + vulnerability_score, 1.0, 2.0)

    # Calculate Human Stress Index
    fused_df["Human_Stress_Index"] = fused_df["WBGT_Celsius"] * risk_multiplier

    fused_df = fused_df.round(3)
    fused_df.to_csv(output_csv_path, index=False)
    print(f"Data fused successfully! Saved final training dataset to: {output_csv_path}")
    return fused_df


if __name__ == "__main__":
    WBGT_CSV = "./data/kolkata_timeseries_wbgt_final.csv"
    CENSUS_XLSX = "DDW_PCA1916_2011_MDDS with UI.xlsx"
    FINAL_OUTPUT = "./data/kolkata_final_hsi_dashboard.csv"

    merge_wbgt_with_real_census(WBGT_CSV, CENSUS_XLSX, FINAL_OUTPUT)
