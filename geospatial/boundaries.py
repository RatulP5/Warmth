"""Geospatial Boundaries, Projections, and Weather Mapping.

Combines:
1. Projected coordinate transformations (EPSG:4326 to EPSG:32645 for Kolkata)
2. Ward boundary validation, polygon standardization, and metric area (m²)
3. Meteorological spatial mapping (IDW, nearest station, bilinear interpolation)
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pyproj
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import transform
from shapely.validation import make_valid

from ingestion.osm import KOLKATA_FALLBACK_ZONES


def reproject_geometry(geom, from_crs: str = "EPSG:4326", to_crs: str = "EPSG:32645"):
    """Reproject geometry from source to target projected CRS."""
    trans = pyproj.Transformer.from_crs(from_crs, to_crs, always_xy=True)
    return transform(trans.transform, geom)


def compute_projected_area_m2(geom, from_crs: str = "EPSG:4326", projected_crs: str = "EPSG:32645") -> float:
    """Compute true surface area in square meters (m²) using projected CRS."""
    return float(reproject_geometry(geom, from_crs, projected_crs).area)


class WardBoundaryManager:
    """Manages ingestion and spatial integrity of ward boundary polygons."""

    def __init__(self, target_crs: str = "EPSG:4326", projected_crs: str = "EPSG:32645"):
        self.target_crs = target_crs
        self.projected_crs = projected_crs

    def load_ward_boundaries(
        self,
        filepath: Optional[str] = None,
        city_name: str = "Kolkata",
        demo_mode: bool = False,
    ) -> gpd.GeoDataFrame:
        """Load, validate, and standardize ward boundary GeoDataFrame."""
        if filepath and Path(filepath).exists() and not demo_mode:
            gdf = gpd.read_file(filepath)
            return self._standardize_and_validate(gdf, city_name)
        return self.create_demo_ward_polygons(city_name)

    def _standardize_and_validate(self, gdf: gpd.GeoDataFrame, city_name: str) -> gpd.GeoDataFrame:
        gdf_out = gdf.copy()
        if gdf_out.crs is None:
            gdf_out.set_crs(self.target_crs, inplace=True)
        elif gdf_out.crs.to_string() != self.target_crs:
            gdf_out = gdf_out.to_crs(self.target_crs)

        if "ward_id" not in gdf_out.columns:
            gdf_out["ward_id"] = [f"WARD_{i+1:03d}" for i in range(len(gdf_out))]
        if "city" not in gdf_out.columns:
            gdf_out["city"] = city_name

        gdf_out["geometry"] = gdf_out["geometry"].apply(lambda g: make_valid(g) if not g.is_valid else g)
        gdf_out = gdf_out.drop_duplicates(subset=["ward_id"]).reset_index(drop=True)
        gdf_out["area_m2"] = [
            compute_projected_area_m2(g, self.target_crs, self.projected_crs) for g in gdf_out["geometry"]
        ]
        gdf_out["lat"] = gdf_out["geometry"].centroid.y
        gdf_out["lon"] = gdf_out["geometry"].centroid.x
        return gdf_out

    def create_demo_ward_polygons(self, city_name: str = "Kolkata") -> gpd.GeoDataFrame:
        """Create valid synthetic polygon boundaries around Kolkata microclimate centroids."""
        records = []
        delta = 0.015
        for z in KOLKATA_FALLBACK_ZONES:
            poly = Polygon([
                (z["lon"] - delta, z["lat"] - delta),
                (z["lon"] + delta, z["lat"] - delta),
                (z["lon"] + delta, z["lat"] + delta),
                (z["lon"] - delta, z["lat"] + delta),
                (z["lon"] - delta, z["lat"] - delta),
            ])
            records.append({
                "ward_id": z["ward_id"],
                "ward_name": z["ward_name"],
                "city": city_name,
                "geometry": poly,
                "lat": z["lat"],
                "lon": z["lon"],
            })
        gdf = gpd.GeoDataFrame(records, crs=self.target_crs)
        gdf["area_m2"] = [
            compute_projected_area_m2(g, self.target_crs, self.projected_crs) for g in gdf["geometry"]
        ]
        return gdf


class WeatherToWardMapper:
    """Maps continuous weather fields or station networks to ward centroids."""

    def __init__(self, idw_power: float = 2.0):
        self.idw_power = idw_power

    def map_inverse_distance_weighting(
        self,
        ward_id: str,
        ward_lat: float,
        ward_lon: float,
        station_df: pd.DataFrame,
        value_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Interpolate station weather to ward centroid using IDW."""
        if value_columns is None:
            value_columns = ["temperature_c", "relative_humidity_pct", "wind_speed_mps", "solar_radiation_wm2"]

        dists = np.sqrt((station_df["lat"] - ward_lat) ** 2 + (station_df["lon"] - ward_lon) ** 2).values
        if np.any(dists < 1e-6):
            idx = np.where(dists < 1e-6)[0][0]
            res = {col: float(station_df[col].iloc[idx]) for col in value_columns}
            res["ward_id"] = ward_id
            return res

        weights = 1.0 / (dists**self.idw_power)
        norm_weights = weights / np.sum(weights)

        interpolated = {"ward_id": ward_id}
        for col in value_columns:
            if col in station_df.columns:
                interpolated[col] = round(float(np.sum(station_df[col].values * norm_weights)), 2)
        return interpolated
