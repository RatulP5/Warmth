"""Unified Spatial Feature Extraction Engine.

Extracts:
1. Zonal statistical distributions (mean, median, p10, p90) for raster arrays
2. Sentinel-2 NDVI, Landsat LST, and WorldCover fractions
3. OpenStreetMap urban morphology (building density, road density, cooling buffers, tin roofs)
4. Construction Exposure Index (CEI) proxy
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from ingestion.satellite import Sentinel2Processor, LandsatLSTProcessor, LandCoverProcessor
from ingestion.osm import OverpassClient


def compute_zonal_statistics(
    raster_data: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Compute descriptive statistics of gridded data within polygon zones."""
    pixels = raster_data[mask] if mask is not None else raster_data.flatten()
    pixels = pixels[~np.isnan(pixels)]
    if len(pixels) == 0:
        return {"count": 0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "std": 0.0, "p10": 0.0, "p90": 0.0}
    return {
        "count": int(len(pixels)),
        "mean": round(float(np.mean(pixels)), 3),
        "median": round(float(np.median(pixels)), 3),
        "min": round(float(np.min(pixels)), 3),
        "max": round(float(np.max(pixels)), 3),
        "std": round(float(np.std(pixels)), 3),
        "p10": round(float(np.percentile(pixels, 10)), 3),
        "p90": round(float(np.percentile(pixels, 90)), 3),
    }


class RasterFeatureExtractor:
    """Extracts satellite features across Sentinel-2, Landsat, and WorldCover."""

    def __init__(self):
        self.sentinel_proc = Sentinel2Processor()
        self.lst_proc = LandsatLSTProcessor()
        self.lc_proc = LandCoverProcessor()

    def extract_ward_raster_features(self, ward_id: str, demo_mode: bool = False) -> Dict[str, Any]:
        ndvi_raster = self.sentinel_proc.generate_synthetic_raster()
        ndvi_stats = self.sentinel_proc.extract_ward_zonal_ndvi(ward_id, ndvi_raster)

        lst_raster = self.lst_proc.generate_synthetic_lst_raster()
        lst_stats = self.lst_proc.extract_ward_zonal_lst(ward_id, lst_raster)

        lc_raster = self.lc_proc.generate_synthetic_landcover_raster()
        lc_stats = self.lc_proc.compute_ward_landcover_fractions(ward_id, lc_raster)

        combined = {"ward_id": ward_id}
        combined.update(ndvi_stats)
        combined.update(lst_stats)
        combined.update(lc_stats)
        return combined


class VectorFeatureExtractor:
    """Extracts morphology from OpenStreetMap vector layers."""

    def __init__(self):
        self.osm_client = OverpassClient()

    def extract_ward_vector_features(
        self,
        ward_id: str,
        lat: float,
        lon: float,
        area_m2: float = 3000000.0,
        demo_mode: bool = False,
    ) -> Dict[str, Any]:
        counts = self.osm_client.fetch_urban_features(lat, lon, demo_mode=demo_mode)
        area_km2 = max(0.1, area_m2 / 1_000_000.0)
        bld_count = counts.get("total_buildings", 0)
        road_count = counts.get("road_segments", 0)
        const_count = counts.get("construction_sites", 0)

        return {
            "ward_id": ward_id,
            "building_count": bld_count,
            "building_density": round(bld_count / area_km2, 1),
            "road_length_km": round(road_count * 0.1, 2),
            "road_density": round((road_count * 0.1) / area_km2, 2),
            "construction_site_count": const_count,
            "construction_density": round(const_count / area_km2, 2),
            "tin_roofs_count": counts.get("tin_roofs", 0),
            "cooling_buffers_count": counts.get("cooling_buffers", 0),
        }

    def compute_construction_exposure_index(
        self,
        construction_density: float,
        outdoor_worker_density: float,
        max_construction_density: float = 10.0,
        max_worker_density: float = 5000.0,
    ) -> float:
        """Standardized construction exposure index proxy (0.0 to 1.0)."""
        c_norm = min(1.0, max(0.0, construction_density / max(1.0, max_construction_density)))
        w_norm = min(1.0, max(0.0, outdoor_worker_density / max(1.0, max_worker_density)))
        return round(float(np.sqrt(c_norm * w_norm)), 3)
