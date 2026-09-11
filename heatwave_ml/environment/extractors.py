"""
extractors.py
─────────────
High-Resolution Environmental Data Extraction Module (Step 3).

100% Real, Authoritative Geospatial Sources:
  1. Land Surface Temperature (LST):
     - Source: USGS Landsat 8/9 Collection 2 Level-2 Surface Temperature (ST_B10 / lwir11)
     - Scale/Offset: LST_K = raw * 0.00341802 + 149.0; LST_C = LST_K - 273.15
     - Cloud Mask: QA_PIXEL bits 1 (dilated cloud), 2 (cirrus), 3 (cloud), 4 (cloud shadow)
     - Valid bounds: [-10, 85] degC
  2. Vegetation Fraction & NDVI:
     - Source: ESA Sentinel-2 L2A Red (B04) and NIR (B08) at 10m
     - NDVI = (B08 - B04) / (B08 + B04)
     - Cloud Mask: SCL band (Scene Classification Layer) valid classes [4, 5, 6]
     - Vegetation fraction: pixels with NDVI > 0.25
  3. Water-Body Fraction & NDWI:
     - Source: ESA Sentinel-2 L2A Green (B03) and NIR (B08)
     - NDWI = (B03 - B08) / (B03 + B08)
     - Water fraction: pixels with NDWI > 0.30
  4. Built-Up & Impervious Surface Fraction (NDBI):
     - Source: ESA Sentinel-2 L2A SWIR (B11) and NIR (B08)
     - NDBI = (B11 - B08) / (B11 + B08)
     - Built-up fraction: pixels with NDBI > 0.0
  5. OpenStreetMap Building Footprints & Road Density:
     - Fetched via OSMnx with persistent caching.
     - Strict 3s timeout to fail fast to NaN when public Overpass servers are congested.
"""

import warnings
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import pystac_client
import planetary_computer
import rioxarray
import xarray as xr
from shapely.geometry import box

try:
    from . import config as cfg
except ImportError:
    import config as cfg

# Fast timeout on public OSMnx requests to avoid deadlocks
ox.settings.requests_timeout = 3


def _catalog() -> pystac_client.Client:
    return pystac_client.Client.open(
        cfg.PC_STAC_URL,
        modifier=planetary_computer.sign_inplace,
    )


class CitySatelliteExtractor:
    """
    Fetches city-extent satellite rasters once per monthly window and computes
    authentic ward zonal statistics locally in memory.
    """

    def __init__(self):
        self._cat: Optional[pystac_client.Client] = None

    def _get_catalog(self) -> pystac_client.Client:
        if self._cat is None:
            self._cat = _catalog()
        return self._cat

    def get_city_lst_raster(
        self,
        city_bbox_4326: list[float],
        date_start: str,
        date_end: str,
    ) -> Tuple[Optional[xr.DataArray], Optional[str]]:
        """
        Retrieves calibrated Landsat 8/9 LST in Celsius for the city bounding box.
        """
        try:
            cat = self._get_catalog()
            items = list(cat.search(
                collections=["landsat-c2-l2"],
                bbox=city_bbox_4326,
                datetime=f"{date_start}/{date_end}",
                query={"platform": {"in": ["landsat-8", "landsat-9"]}},
                sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}],
                max_items=3,
            ).items())

            if not items:
                return None, None

            for item in items:
                assets = item.assets
                if "lwir11" not in assets or "qa_pixel" not in assets:
                    continue

                da_lst = rioxarray.open_rasterio(assets["lwir11"].href, masked=True, lock=False)
                da_qa  = rioxarray.open_rasterio(assets["qa_pixel"].href, masked=True, lock=False)

                city_box_native = gpd.GeoSeries([box(*city_bbox_4326)], crs=f"EPSG:{cfg.WGS84_EPSG}").to_crs(da_lst.rio.crs)
                bbox_native = list(city_box_native.total_bounds)

                sub_lst = da_lst.rio.clip_box(*bbox_native).load()
                sub_qa  = da_qa.rio.clip_box(*bbox_native).load()

                min_r = min(sub_lst.shape[-2], sub_qa.shape[-2])
                min_c = min(sub_lst.shape[-1], sub_qa.shape[-1])
                sub_lst = sub_lst[..., :min_r, :min_c]
                sub_qa  = sub_qa[..., :min_r, :min_c]

                raw_data = sub_lst.values.squeeze().astype(np.float32)
                qa_data  = sub_qa.values.squeeze()

                lst_c = raw_data * cfg.LST_SCALE + cfg.LST_OFFSET + cfg.LST_K_TO_C

                qa_int = np.where(np.isfinite(qa_data), qa_data, 0).astype(np.uint16)
                cloud_mask = (
                    ((qa_int & (1 << 1)) != 0) |
                    ((qa_int & (1 << 2)) != 0) |
                    ((qa_int & (1 << 3)) != 0) |
                    ((qa_int & (1 << 4)) != 0)
                )

                lst_c[cloud_mask] = np.nan
                lst_c[raw_data == 0] = np.nan
                lst_c[(lst_c < -10) | (lst_c > 85)] = np.nan

                lst_da = xr.DataArray(
                    lst_c,
                    coords={"y": sub_lst.y[:min_r], "x": sub_lst.x[:min_c]},
                    dims=["y", "x"],
                ).rio.write_crs(sub_lst.rio.crs).rio.write_transform(sub_lst.rio.transform())

                source_date = str(item.datetime.date())
                return lst_da, source_date

            return None, None
        except Exception as e:
            warnings.warn(f"[CitySatelliteExtractor] Landsat fetch failed: {e}")
            return None, None

    def get_city_sentinel_rasters(
        self,
        city_bbox_4326: list[float],
        date_start: str,
        date_end: str,
    ) -> Tuple[Optional[xr.DataArray], Optional[xr.DataArray], Optional[xr.DataArray], Optional[str]]:
        """
        Retrieves Sentinel-2 L2A rasters: NDVI, NDWI, NDBI (built-up), and source date.
        """
        try:
            cat = self._get_catalog()
            items = list(cat.search(
                collections=["sentinel-2-l2a"],
                bbox=city_bbox_4326,
                datetime=f"{date_start}/{date_end}",
                query={"eo:cloud_cover": {"lt": cfg.MAX_CLOUD_COVER}},
                sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}],
                max_items=3,
            ).items())

            if not items:
                return None, None, None, None

            for item in items:
                assets = item.assets
                req_bands = {"B04", "B08", "B03"}
                if not req_bands.issubset(assets):
                    continue

                da_red = rioxarray.open_rasterio(assets["B04"].href, masked=True, lock=False)
                da_nir = rioxarray.open_rasterio(assets["B08"].href, masked=True, lock=False)
                da_grn = rioxarray.open_rasterio(assets["B03"].href, masked=True, lock=False)

                city_box_native = gpd.GeoSeries([box(*city_bbox_4326)], crs=f"EPSG:{cfg.WGS84_EPSG}").to_crs(da_red.rio.crs)
                bbox_native = list(city_box_native.total_bounds)

                sub_red = da_red.rio.clip_box(*bbox_native).load()
                sub_nir = da_nir.rio.clip_box(*bbox_native).load()
                sub_grn = da_grn.rio.clip_box(*bbox_native).load()

                # B11 (SWIR) for NDBI / Built-up index
                sub_swir = None
                if "B11" in assets:
                    da_swir = rioxarray.open_rasterio(assets["B11"].href, masked=True, lock=False)
                    sub_swir_raw = da_swir.rio.clip_box(*bbox_native).load()
                    sub_swir = sub_swir_raw.rio.reproject_match(sub_red)

                min_r = min(sub_red.shape[-2], sub_nir.shape[-2], sub_grn.shape[-2])
                min_c = min(sub_red.shape[-1], sub_nir.shape[-1], sub_grn.shape[-1])
                sub_red = sub_red[..., :min_r, :min_c]
                sub_nir = sub_nir[..., :min_r, :min_c]
                sub_grn = sub_grn[..., :min_r, :min_c]

                red_val = sub_red.values.squeeze().astype(np.float32)
                nir_val = sub_nir.values.squeeze().astype(np.float32)
                grn_val = sub_grn.values.squeeze().astype(np.float32)

                eps = 1e-6
                ndvi_arr = (nir_val - red_val) / (nir_val + red_val + eps)
                ndwi_arr = (grn_val - nir_val) / (grn_val + nir_val + eps)

                if sub_swir is not None:
                    swir_val = sub_swir.values.squeeze()[:min_r, :min_c].astype(np.float32)
                    ndbi_arr = (swir_val - nir_val) / (swir_val + nir_val + eps)
                else:
                    ndbi_arr = None

                # SCL cloud masking
                if "SCL" in assets:
                    da_scl = rioxarray.open_rasterio(assets["SCL"].href, masked=True, lock=False)
                    sub_scl = da_scl.rio.clip_box(*bbox_native).load()
                    sub_scl_aligned = sub_scl.rio.reproject_match(sub_red)
                    scl_val = sub_scl_aligned.values.squeeze()[:min_r, :min_c]
                    scl_int = np.where(np.isfinite(scl_val), scl_val, 0).astype(np.uint8)
                    valid_scl = np.isin(scl_int, [4, 5, 6])
                    ndvi_arr[~valid_scl] = np.nan
                    ndwi_arr[~valid_scl] = np.nan
                    if ndbi_arr is not None:
                        ndbi_arr[~valid_scl] = np.nan

                # Wrap into DataArrays
                coords = {"y": sub_red.y[:min_r], "x": sub_red.x[:min_c]}
                ndvi_da = xr.DataArray(ndvi_arr, coords=coords, dims=["y", "x"]).rio.write_crs(sub_red.rio.crs).rio.write_transform(sub_red.rio.transform())
                ndwi_da = xr.DataArray(ndwi_arr, coords=coords, dims=["y", "x"]).rio.write_crs(sub_red.rio.crs).rio.write_transform(sub_red.rio.transform())

                if ndbi_arr is not None:
                    ndbi_da = xr.DataArray(ndbi_arr, coords=coords, dims=["y", "x"]).rio.write_crs(sub_red.rio.crs).rio.write_transform(sub_red.rio.transform())
                else:
                    ndbi_da = None

                source_date = str(item.datetime.date())
                return ndvi_da, ndwi_da, ndbi_da, source_date

            return None, None, None, None
        except Exception as e:
            warnings.warn(f"[CitySatelliteExtractor] Sentinel-2 fetch failed: {e}")
            return None, None, None, None


class CachedOsmExtractor:
    """
    Extracts building footprints and highway networks with on-disk caching.
    Uses a 3s timeout to never hang if public Overpass servers are down.
    """

    def __init__(self, cache_path: str = str(cfg.PROCESSED_DIR / "osm_morphology_cache.parquet")):
        self.cache_path = Path(cache_path)
        self.cache: dict[str, dict] = {}
        self._overpass_available: Optional[bool] = None
        self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            df = pd.read_parquet(self.cache_path)
            for _, r in df.iterrows():
                self.cache[r["ward_id"]] = {
                    "osm_bcr":          r.get("osm_bcr", np.nan),
                    "road_density_m_km2": r.get("road_density_m_km2", np.nan),
                }

    def _is_overpass_alive(self) -> bool:
        if self._overpass_available is not None:
            return self._overpass_available
        import urllib.request
        try:
            req = urllib.request.Request(
                "https://overpass-api.de/api/status",
                headers={"User-Agent": "Warmth/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                self._overpass_available = (resp.status == 200)
        except Exception:
            self._overpass_available = False

        if not self._overpass_available:
            warnings.warn(
                "[CachedOsmExtractor] Public Overpass server is unavailable/timed out. "
                "OSM metrics will be set to NaN (strictly no fabrication); "
                "satellite NDBI will supply the built-up/impervious surface fraction."
            )
        return self._overpass_available

    def save_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        records = [{"ward_id": k, **v} for k, v in self.cache.items()]
        if records:
            pd.DataFrame(records).to_parquet(self.cache_path, index=False)

    def get_builtup_road(self, ward_id: str, ward_polygon_4326, ward_utm_geom) -> dict:
        if ward_id in self.cache:
            return self.cache[ward_id]

        if not self._is_overpass_alive():
            res = {"osm_bcr": np.nan, "road_density_m_km2": np.nan}
            self.cache[ward_id] = res
            return res

        total_area_sqm = ward_utm_geom.area
        total_area_km2 = total_area_sqm / 1e6

        osm_bcr = np.nan
        try:
            blds = ox.features_from_polygon(ward_polygon_4326, tags={"building": True})
            if not blds.empty:
                blds_utm = blds.to_crs(epsg=cfg.KOLKATA_UTM_EPSG)
                built_sqm = float(blds_utm.geometry.area.sum())
                osm_bcr = round(min(built_sqm / total_area_sqm, 1.0), 4)
        except Exception:
            osm_bcr = np.nan

        road_dens = np.nan
        try:
            roads = ox.features_from_polygon(ward_polygon_4326, tags={"highway": True})
            if not roads.empty:
                roads_utm = roads.to_crs(epsg=cfg.KOLKATA_UTM_EPSG)
                road_m = float(roads_utm.geometry.length.sum())
                road_dens = round(road_m / max(total_area_km2, 1e-6), 1)
        except Exception:
            road_dens = np.nan

        res = {
            "osm_bcr":          osm_bcr,
            "road_density_m_km2": road_dens,
        }
        self.cache[ward_id] = res
        return res
