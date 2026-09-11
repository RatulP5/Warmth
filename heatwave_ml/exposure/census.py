"""
heatwave_ml/exposure/census.py
──────────────────────────────
Extracts ward-level demographic exposure features and outdoor labor proxies
from the official Census 2011 Primary Census Abstract (PCA).
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.ops import transform as shp_transform

try:
    from . import config as cfg
except ImportError:
    import config as cfg


class CensusExposureLoader:
    """
    Loads Census 2011 PCA data and computes:
      - Total ward population (TOT_P)
      - Population density per km2 (derived via ward geometry)
      - Potential outdoor labor exposure proxy (cultivators, agricultural labor,
        and other manual/service workers outside household industry)
      - Relative outdoor exposure score (0-1 normalized across wards)
    """

    def __init__(
        self,
        census_path: str = cfg.CENSUS_PATH,
        geojson_path: str = cfg.GEOJSON_PATH,
    ):
        self.census_path = census_path
        self.geojson_path = geojson_path
        self._df: pd.DataFrame | None = None

    @staticmethod
    def _swap_xy(geom):
        """Correct the (lat, lon) -> (lon, lat) coordinate order in the KMC GeoJSON."""
        return shp_transform(
            lambda x, y, z=None: (y, x) if z is None else (y, x, z),
            geom,
        )

    def _load_ward_areas(self) -> dict[str, float]:
        """Load ward polygons and compute area in square kilometers."""
        gdf = gpd.read_file(self.geojson_path)
        ward_col = "WARD" if "WARD" in gdf.columns else "Name"
        gdf["ward_num"] = (
            gdf[ward_col]
            .astype(str)
            .str.strip()
            .str.extract(r"(\d+)", expand=False)
            .astype(int)
        )
        gdf["ward_id"] = "KMC_Ward_" + gdf["ward_num"].astype(str)
        gdf["geometry"] = gdf["geometry"].apply(self._swap_xy)
        gdf = gdf.set_geometry("geometry").set_crs(epsg=cfg.WGS84_EPSG, allow_override=True)
        gdf_utm = gdf.to_crs(epsg=cfg.KOLKATA_UTM_EPSG)

        areas_km2 = {}
        for _, row in gdf_utm.iterrows():
            areas_km2[row["ward_id"]] = row.geometry.area / 1e6
        return areas_km2

    def load(self) -> pd.DataFrame:
        """Process Census PCA and return standardized exposure features per ward."""
        if self._df is not None:
            return self._df

        pca_df = pd.read_excel(self.census_path, sheet_name=0)
        ward_mask = pca_df["Level"].astype(str).str.strip().str.upper() == "WARD"
        wards = pca_df[ward_mask].copy()

        wards["ward_num"] = wards["Ward"].astype(int)
        wards["ward_id"] = "KMC_Ward_" + wards["ward_num"].astype(str)

        ward_areas = self._load_ward_areas()

        records = []
        for _, row in wards.iterrows():
            wid = row["ward_id"]
            tot_p = int(row["TOT_P"])
            area_km2 = ward_areas.get(wid, np.nan)

            pop_density = (
                round(tot_p / area_km2, 2)
                if area_km2 and not np.isnan(area_km2) and area_km2 > 0
                else np.nan
            )

            # Outdoor labor proxies:
            # Main agricultural laborers, cultivators, and general non-household workers (manual/field labor)
            # plus corresponding marginal worker categories
            main_outdoor = int(row.get("MAIN_CL_P", 0) + row.get("MAIN_AL_P", 0) + row.get("MAIN_OT_P", 0))
            marg_outdoor = int(row.get("MARG_CL_P", 0) + row.get("MARG_AL_P", 0) + row.get("MARG_OT_P", 0))
            total_outdoor = main_outdoor + marg_outdoor

            outdoor_frac = round(total_outdoor / max(tot_p, 1), 4)

            records.append({
                "ward_id":                  wid,
                "ward_num":                 int(row["ward_num"]),
                "ward_name":                str(row.get("Name", "")).strip(),
                "population":               tot_p,
                "ward_area_km2":            round(area_km2, 4) if np.isfinite(area_km2) else np.nan,
                "population_density_km2":   pop_density,
                "outdoor_labor_population": total_outdoor,
                "outdoor_labor_fraction":   outdoor_frac,
                "is_proxy":                 True,
                "source":                   "Census 2011 Primary Census Abstract",
                "source_year":              2011,
            })

        df = pd.DataFrame(records)

        # Min-max normalized outdoor exposure score (0.0 to 1.0)
        min_val = df["outdoor_labor_fraction"].min()
        max_val = df["outdoor_labor_fraction"].max()
        if max_val > min_val:
            df["outdoor_exposure_score"] = (
                (df["outdoor_labor_fraction"] - min_val) / (max_val - min_val)
            ).round(4)
        else:
            df["outdoor_exposure_score"] = 0.0

        self._df = df
        return df
