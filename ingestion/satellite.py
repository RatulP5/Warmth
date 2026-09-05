"""Unified Satellite Ingestion and Zonal Processing Engine.

Combines:
1. Copernicus Sentinel-2 MSI (NDVI and canopy cover)
2. USGS Landsat 8/9 TIRS (Land Surface Temperature & thermal anomalies)
3. ESA WorldCover 10m (Surface class fractions)
"""

from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np


class Sentinel2Processor:
    """Processor for Sentinel-2 MSI surface reflectance."""

    def compute_ndvi_raster(
        self, b04_red: np.ndarray, b08_nir: np.ndarray, cloud_mask: Optional[np.ndarray] = None
    ) -> np.ndarray:
        red = b04_red.astype(float)
        nir = b08_nir.astype(float)
        denom = nir + red
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi = np.where(denom != 0.0, (nir - red) / denom, np.nan)
        ndvi = np.clip(ndvi, -1.0, 1.0)
        if cloud_mask is not None:
            ndvi[cloud_mask] = np.nan
        return ndvi

    def extract_ward_zonal_ndvi(
        self, ward_id: str, ndvi_array: np.ndarray, pixel_size_m: float = 10.0
    ) -> Dict[str, Any]:
        valid = ndvi_array[~np.isnan(ndvi_array)]
        if len(valid) == 0:
            return {
                "ward_id": ward_id, "ndvi_mean": 0.0, "ndvi_median": 0.0,
                "ndvi_min": 0.0, "ndvi_max": 0.0, "ndvi_std": 0.0,
                "ndvi_p10": 0.0, "ndvi_p90": 0.0, "vegetation_percentage": 0.0,
                "high_vegetation_percentage": 0.0,
            }
        veg_mask = valid >= 0.20
        high_veg_mask = valid >= 0.40
        return {
            "ward_id": ward_id,
            "ndvi_mean": round(float(np.mean(valid)), 3),
            "ndvi_median": round(float(np.median(valid)), 3),
            "ndvi_min": round(float(np.min(valid)), 3),
            "ndvi_max": round(float(np.max(valid)), 3),
            "ndvi_std": round(float(np.std(valid)), 3),
            "ndvi_p10": round(float(np.percentile(valid, 10)), 3),
            "ndvi_p90": round(float(np.percentile(valid, 90)), 3),
            "vegetation_percentage": round((np.sum(veg_mask) / len(valid)) * 100.0, 2),
            "high_vegetation_percentage": round((np.sum(high_veg_mask) / len(valid)) * 100.0, 2),
            "source": "Sentinel-2 MSI Level-2A",
        }

    def generate_synthetic_raster(self, width: int = 100, height: int = 100, urban_ratio: float = 0.7) -> np.ndarray:
        base = np.random.uniform(0.05, 0.25, (height, width))
        parks = np.random.uniform(0.35, 0.65, (height, width))
        mask = np.random.rand(height, width) > urban_ratio
        return np.where(mask, parks, base)


class LandsatLSTProcessor:
    """Processor for Landsat Thermal Infrared Sensor (TIRS) Land Surface Temperature."""

    def extract_ward_zonal_lst(
        self, ward_id: str, lst_celsius_array: np.ndarray, baseline_lst_celsius: float = 34.0
    ) -> Dict[str, Any]:
        valid = lst_celsius_array[~np.isnan(lst_celsius_array)]
        if len(valid) == 0:
            return {
                "ward_id": ward_id, "lst_mean_c": 0.0, "lst_median_c": 0.0,
                "lst_min_c": 0.0, "lst_max_c": 0.0, "lst_std_c": 0.0,
                "lst_p10_c": 0.0, "lst_p90_c": 0.0, "lst_anomaly_c": 0.0,
            }
        mean_val = float(np.mean(valid))
        return {
            "ward_id": ward_id,
            "lst_mean_c": round(mean_val, 2),
            "lst_median_c": round(float(np.median(valid)), 2),
            "lst_min_c": round(float(np.min(valid)), 2),
            "lst_max_c": round(float(np.max(valid)), 2),
            "lst_std_c": round(float(np.std(valid)), 2),
            "lst_p10_c": round(float(np.percentile(valid, 10)), 2),
            "lst_p90_c": round(float(np.percentile(valid, 90)), 2),
            "lst_anomaly_c": round(mean_val - baseline_lst_celsius, 2),
            "source": "Landsat 8/9 TIRS Band 10",
        }

    def generate_synthetic_lst_raster(self, width: int = 100, height: int = 100, mean_temp: float = 38.0) -> np.ndarray:
        base = np.random.normal(mean_temp, 2.5, (height, width))
        hotspots = np.random.uniform(42.0, 48.0, (height, width))
        mask = np.random.rand(height, width) < 0.2
        return np.where(mask, hotspots, base)


class LandCoverProcessor:
    """Processor for ESA WorldCover 10m land surface partitioning."""

    CLASS_MAP = {10: "tree_cover", 30: "grassland", 50: "built_up", 80: "water"}

    def compute_ward_landcover_fractions(self, ward_id: str, class_raster: np.ndarray) -> Dict[str, Any]:
        valid = class_raster[~np.isnan(class_raster)]
        total = len(valid)
        if total == 0:
            return {
                "ward_id": ward_id, "tree_cover_percentage": 0.0,
                "grass_cover_percentage": 0.0, "built_up_percentage": 0.0,
                "water_percentage": 0.0,
            }
        counts = {name: 0 for name in self.CLASS_MAP.values()}
        unique, counts_arr = np.unique(valid, return_counts=True)
        for code, cnt in zip(unique, counts_arr):
            name = self.CLASS_MAP.get(int(code))
            if name:
                counts[name] = int(cnt)
        return {
            "ward_id": ward_id,
            "tree_cover_percentage": round((counts["tree_cover"] / total) * 100.0, 2),
            "grass_cover_percentage": round((counts["grassland"] / total) * 100.0, 2),
            "built_up_percentage": round((counts["built_up"] / total) * 100.0, 2),
            "water_percentage": round((counts["water"] / total) * 100.0, 2),
            "source": "ESA WorldCover 10m",
        }

    def generate_synthetic_landcover_raster(self, width: int = 100, height: int = 100) -> np.ndarray:
        choices = [50, 10, 30, 80]
        p = [0.60, 0.20, 0.10, 0.10]
        return np.random.choice(choices, size=(height, width), p=p)
