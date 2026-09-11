"""
pipeline.py
───────────
Step 3: High-Resolution Environmental Feature Pipeline.

Produces authentic ward-level environmental features:
  - LST statistics (mean, median, p90) from USGS Landsat 8/9 Level-2
  - NDVI & Vegetation Fraction from ESA Sentinel-2 L2A (10m)
  - NDWI & Water Fraction from ESA Sentinel-2 L2A (10m)
  - Built-Up / Impervious Fraction from Sentinel-2 NDBI (SWIR/NIR)
  - OpenStreetMap morphology (building BCR & road density) from local cache

Zero data fabrication: missing or cloud-obscured data is recorded as NaN.
"""

import argparse
import time
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import transform as shp_transform

try:
    from . import config as cfg
    from .extractors import CitySatelliteExtractor, CachedOsmExtractor
except ImportError:
    import config as cfg
    from extractors import CitySatelliteExtractor, CachedOsmExtractor


class WardLoader:
    """
    Loads KMC ward GeoJSON and fixes the (lat, lon) -> (lon, lat) coordinate swap.
    """

    def __init__(self, geojson_path: str = cfg.GEOJSON_PATH):
        self.geojson_path = geojson_path
        self._gdf_4326: gpd.GeoDataFrame | None = None
        self._gdf_utm:  gpd.GeoDataFrame | None = None

    @staticmethod
    def _swap_xy(geom):
        return shp_transform(
            lambda x, y, z=None: (y, x) if z is None else (y, x, z),
            geom,
        )

    def load(self) -> gpd.GeoDataFrame:
        if self._gdf_4326 is not None:
            return self._gdf_4326

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

        self._gdf_4326 = gdf.copy()
        self._gdf_utm  = gdf.to_crs(epsg=cfg.KOLKATA_UTM_EPSG)
        return self._gdf_4326

    def get_utm(self) -> gpd.GeoDataFrame:
        if self._gdf_utm is None:
            self.load()
        return self._gdf_utm


def _calc_stats(arr: np.ndarray) -> dict:
    valid = arr.flatten()
    valid = valid[np.isfinite(valid)]
    if len(valid) == 0:
        return {"mean": np.nan, "median": np.nan, "p90": np.nan, "valid_px": 0}
    return {
        "mean":     float(np.mean(valid)),
        "median":   float(np.median(valid)),
        "p90":      float(np.percentile(valid, 90)),
        "valid_px": int(len(valid)),
    }


class EnvironmentPipeline:
    def __init__(self, geojson_path: str = cfg.GEOJSON_PATH):
        self.loader = WardLoader(geojson_path)
        self.sat_ext = CitySatelliteExtractor()
        self.osm_ext = CachedOsmExtractor()

    def run(
        self,
        output_path: str = cfg.OUTPUT_PATH,
        ward_ids: list[str] | None = None,
        months:   list[tuple[str, str]] | None = None,
        fetch_osm: bool = False,
    ) -> pd.DataFrame:
        t0 = time.time()
        gdf_4326 = self.loader.load()
        gdf_utm  = self.loader.get_utm()
        months   = months or cfg.MONTHLY_WINDOWS

        if ward_ids:
            gdf_4326 = gdf_4326[gdf_4326["ward_id"].isin(ward_ids)].copy()
            gdf_utm  = gdf_utm[gdf_utm["ward_id"].isin(ward_ids)].copy()

        city_bbox_4326 = list(gdf_4326.total_bounds)
        n_wards = len(gdf_4326)
        print(f"\n=== [Step 3] Environmental Feature Pipeline Starting ===")
        print(f"    Wards: {n_wards} | Windows: {len(months)} months | Total: {n_wards * len(months)} rows")

        # Step A: Load static urban morphology (from cache or live if requested)
        print("\n--> [A] Loading static urban morphology...", end=" ", flush=True)
        osm_lookup = {}
        if fetch_osm:
            for _, w_row in gdf_4326.iterrows():
                wid = w_row["ward_id"]
                poly_utm = gdf_utm.loc[gdf_utm["ward_id"] == wid, "geometry"].iloc[0]
                osm_lookup[wid] = self.osm_ext.get_builtup_road(wid, w_row.geometry, poly_utm)
            self.osm_ext.save_cache()
        else:
            for wid in gdf_4326["ward_id"]:
                osm_lookup[wid] = self.osm_ext.cache.get(wid, {"osm_bcr": np.nan, "road_density_m_km2": np.nan})
        print(f"Done for {len(osm_lookup)} wards.")

        # Step B: Monthly satellite extraction (Landsat LST + Sentinel-2 optical)
        records = []

        for date_start, date_end in months:
            ym = date_start[:7]
            print(f"\n--> Window: {ym} ({date_start} to {date_end})")

            # 1. Landsat LST
            t_m = time.time()
            print("    [1/3] Streaming Landsat 8/9 LST...", end=" ", flush=True)
            lst_da, lst_date = self.sat_ext.get_city_lst_raster(city_bbox_4326, date_start, date_end)
            if lst_da is not None:
                print(f"Done in {time.time()-t_m:.1f}s (Date: {lst_date})")
            else:
                print("No clear scene found (monsoon cloud cover)")

            # 2. Sentinel-2 optical bands
            t_s = time.time()
            print("    [2/3] Streaming Sentinel-2 (NDVI, NDWI, NDBI)...", end=" ", flush=True)
            ndvi_da, ndwi_da, ndbi_da, s2_date = self.sat_ext.get_city_sentinel_rasters(city_bbox_4326, date_start, date_end)
            if ndvi_da is not None:
                print(f"Done in {time.time()-t_s:.1f}s (Date: {s2_date})")
            else:
                print("No clear scene found (monsoon cloud cover)")

            # 3. Fast in-memory zonal statistics
            print(f"    [3/3] Computing zonal statistics across all {n_wards} wards in memory...", end=" ", flush=True)
            t_z = time.time()

            wards_lst_crs = gdf_4326.to_crs(lst_da.rio.crs) if lst_da is not None else None
            wards_s2_crs  = gdf_4326.to_crs(ndvi_da.rio.crs) if ndvi_da is not None else None

            for _, w_row in gdf_4326.iterrows():
                wid = w_row["ward_id"]

                # LST zonal stats
                if lst_da is not None and wards_lst_crs is not None:
                    w_poly = wards_lst_crs.loc[wards_lst_crs["ward_id"] == wid, "geometry"].iloc[0]
                    try:
                        w_clip = lst_da.rio.clip([w_poly], lst_da.rio.crs, drop=True, all_touched=True).values
                        lst_stats = _calc_stats(w_clip)
                    except Exception:
                        lst_stats = {"mean": np.nan, "median": np.nan, "p90": np.nan, "valid_px": 0}
                else:
                    lst_stats = {"mean": np.nan, "median": np.nan, "p90": np.nan, "valid_px": 0}

                # Sentinel-2 zonal stats
                ndvi_mean, veg_frac, water_frac, builtup_frac = np.nan, np.nan, np.nan, np.nan
                if ndvi_da is not None and wards_s2_crs is not None:
                    w_poly_s2 = wards_s2_crs.loc[wards_s2_crs["ward_id"] == wid, "geometry"].iloc[0]
                    try:
                        ndvi_clip = ndvi_da.rio.clip([w_poly_s2], ndvi_da.rio.crs, drop=True, all_touched=True).values.flatten()
                        v_ndvi = ndvi_clip[np.isfinite(ndvi_clip)]
                        if len(v_ndvi) > 0:
                            ndvi_mean = float(np.mean(v_ndvi))
                            veg_frac = float(np.mean(v_ndvi > cfg.NDVI_VEG_THRESHOLD))
                    except Exception:
                        pass

                    if ndwi_da is not None:
                        try:
                            ndwi_clip = ndwi_da.rio.clip([w_poly_s2], ndwi_da.rio.crs, drop=True, all_touched=True).values.flatten()
                            v_ndwi = ndwi_clip[np.isfinite(ndwi_clip)]
                            if len(v_ndwi) > 0:
                                water_frac = float(np.mean(v_ndwi > cfg.NDWI_WATER_THRESHOLD))
                        except Exception:
                            pass

                    if ndbi_da is not None:
                        try:
                            ndbi_clip = ndbi_da.rio.clip([w_poly_s2], ndbi_da.rio.crs, drop=True, all_touched=True).values.flatten()
                            v_ndbi = ndbi_clip[np.isfinite(ndbi_clip)]
                            if len(v_ndbi) > 0:
                                builtup_frac = float(np.mean(v_ndbi > 0.0))
                        except Exception:
                            pass

                # OSM morphology lookup
                osm_data = osm_lookup.get(wid, {})
                osm_bcr = osm_data.get("osm_bcr", np.nan)
                road_density = osm_data.get("road_density_m_km2", np.nan)

                # Prioritize OSM BCR if present, otherwise satellite NDBI
                final_builtup = osm_bcr if np.isfinite(osm_bcr) else builtup_frac

                # Authentic data quality classification
                has_lst = np.isfinite(lst_stats["mean"])
                has_opt = np.isfinite(ndvi_mean)

                if has_lst and has_opt:
                    quality = "good"
                elif has_lst or has_opt:
                    quality = "partial"
                elif np.isfinite(final_builtup):
                    quality = "morphology_only"
                else:
                    quality = "insufficient"

                records.append({
                    "ward_id":             wid,
                    "year_month":          ym,
                    "lst_mean":            lst_stats["mean"],
                    "lst_median":          lst_stats["median"],
                    "lst_p90":             lst_stats["p90"],
                    "lst_valid_px":        lst_stats["valid_px"],
                    "lst_source_date":     lst_date,
                    "ndvi_mean":           ndvi_mean,
                    "vegetation_fraction": veg_frac,
                    "water_fraction":      water_frac,
                    "builtup_fraction":    final_builtup,
                    "road_density_m_km2":  road_density,
                    "ndvi_source_date":    s2_date,
                    "data_quality":        quality,
                })

            print(f"Done in {time.time()-t_z:.1f}s")

        df = pd.DataFrame(records)
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_file, index=False)

        print(f"\n[EnvironmentPipeline] Complete in {time.time()-t0:.1f}s!")
        print(f"                       Total Records Written: {len(df)}")
        print(f"                       Destination          : {out_file}")
        q_breakdown = df["data_quality"].value_counts().to_dict()
        print(f"                       Quality Breakdown    : {q_breakdown}\n")
        return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Step 3 Environmental Feature Pipeline.")
    parser.add_argument("--ward", nargs="*", default=None, help="Specific ward IDs to process.")
    parser.add_argument("--output", default=cfg.OUTPUT_PATH, help="Output Parquet path.")
    parser.add_argument("--fetch-osm", action="store_true", default=False, help="Perform live Overpass queries (slow). Default is cache-first with satellite NDBI.")
    args = parser.parse_args()

    pipeline = EnvironmentPipeline()
    pipeline.run(output_path=args.output, ward_ids=args.ward, fetch_osm=args.fetch_osm)
