import sys
import json
import pandas as pd
import geopandas as gpd

import config

# Physical feature imports
from physical.bcr import get_building_coverage_ratio
from physical.isf import get_impervious_surface_fraction
from physical.aspect_ratio import get_canyon_aspect_ratio
from physical.gcr import get_green_coverage_ratio

# Social feature imports
from social.children import get_children_ratio
from social.labor import get_outdoor_labor_ratio
from social.crowding import get_household_crowding
from social.non_workers import get_non_worker_ratio
from social.marginality import get_marginality_index


class WardExtractor:
    def __init__(self, geojson_path: str = config.GEOJSON_PATH, pca_path: str = config.PCA_EXCEL_PATH):
        self.geojson_path = geojson_path
        self.pca_path = pca_path
        self._load_data()

    def _load_data(self):
        # 1. Load GeoJSON
        gdf = gpd.read_file(self.geojson_path)

        # Prefer explicit WARD column; fall back to other candidate columns
        if "WARD" in gdf.columns:
            target_col = "WARD"
        else:
            possible_cols = [c for c in gdf.columns if "ward" in c.lower() or c.lower() in ["name", "id", "admin_level_8"]]
            if not possible_cols:
                raise KeyError(f"Could not identify a ward column. Available columns: {gdf.columns.tolist()}")
            target_col = possible_cols[0]
        print(f"Using GeoJSON column '{target_col}' for ward numbers.")

        # Extract numeric integer ID safely (strip whitespace/newlines first)
        gdf["clean_ward"] = (
            gdf[target_col]
            .astype(str)
            .str.strip()
            .str.extract(r"(\d+)", expand=False)
            .astype(int)
        )

        # Fix swapped lat/lon: this GeoJSON stores coordinates as (lat, lon)
        # instead of the GeoJSON standard (lon, lat), so we swap X<->Y.
        from shapely.ops import transform as shp_transform
        def swap_xy(geom):
            return shp_transform(lambda x, y, z=None: (y, x) if z is None else (y, x, z), geom)
        gdf["geometry"] = gdf["geometry"].apply(swap_xy)
        gdf = gdf.set_geometry("geometry").set_crs(epsg=config.WGS84_EPSG, allow_override=True)

        self.gdf_4326 = gdf  # already in 4326 after swap
        self.gdf_utm = gdf.to_crs(epsg=config.KOLKATA_UTM_EPSG)

        # 2. Load Census PCA
        pca_df = pd.read_excel(self.pca_path, sheet_name=0)
        ward_rows = pca_df[pca_df["Level"].astype(str).str.strip().str.upper() == "WARD"].copy()
        ward_rows["clean_ward"] = ward_rows["Ward"].astype(int)
        self.pca_df = ward_rows.set_index("clean_ward")

    def pull_ward_profile(self, ward_no: int) -> dict:
        ward_no = int(ward_no)
        if ward_no not in self.pca_df.index:
            raise ValueError(f"Ward {ward_no} not found in Census PCA.")
        if ward_no not in self.gdf_4326["clean_ward"].values:
            raise ValueError(f"Ward {ward_no} not found in Ward GeoJSON.")

        print(f"--> Extracting data for Kolkata Ward {ward_no}...")

        # 1. Geometry references
        w_4326 = self.gdf_4326[self.gdf_4326["clean_ward"] == ward_no]
        w_utm = self.gdf_utm[self.gdf_utm["clean_ward"] == ward_no]
        poly_4326 = w_4326.geometry.iloc[0]
        geom_utm = w_utm.geometry.iloc[0]
        census_row = self.pca_df.loc[ward_no]

        # 2. Execute Physical Modules
        print("  - Calculating physical features (BCR, ISF, H/W, GCR)...")
        bcr_data = get_building_coverage_ratio(poly_4326, geom_utm)
        isf_data = get_impervious_surface_fraction(poly_4326, geom_utm, bcr_data["built_area_sqm"])
        canyon_data = get_canyon_aspect_ratio(poly_4326)
        green_data = get_green_coverage_ratio(w_4326)

        # 3. Execute Social Modules
        print("  - Calculating social features (Children, Labor, Crowding, Marginality)...")
        children_data = get_children_ratio(census_row)
        labor_data = get_outdoor_labor_ratio(census_row)
        crowd_data = get_household_crowding(census_row)
        non_work_data = get_non_worker_ratio(census_row)
        marginal_data = get_marginality_index(census_row)

        # 4. Construct Unified Output
        profile = {
            "ward_no": ward_no,
            "ward_name": str(census_row["Name"]),
            "total_population": int(census_row["TOT_P"]),
            "total_area_sqkm": round(geom_utm.area / 1e6, 3),
            "physical_features": {
                **bcr_data,
                **isf_data,
                **canyon_data,
                **green_data
            },
            "social_features": {
                **children_data,
                **labor_data,
                **crowd_data,
                **non_work_data,
                **marginal_data
            }
        }
        return profile


if __name__ == "__main__":
    ward_target = int(sys.argv[1]) if len(sys.argv) > 1 else 65
    
    extractor = WardExtractor()
    result = extractor.pull_ward_profile(ward_no=ward_target)
    
    print("\n--- EXTRACTION COMPLETE ---")
    print(json.dumps(result, indent=2))