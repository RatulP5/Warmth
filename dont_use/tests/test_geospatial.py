"""Unit tests for Geospatial Processing, Boundaries, and Spatial Features."""

import unittest
import numpy as np
import pandas as pd

from geospatial.boundaries import WardBoundaryManager, WeatherToWardMapper, compute_projected_area_m2
from geospatial.spatial_features import compute_zonal_statistics, VectorFeatureExtractor


class TestGeospatialEngine(unittest.TestCase):
    def setUp(self):
        self.boundary_mgr = WardBoundaryManager()
        self.weather_mapper = WeatherToWardMapper()
        self.vector_extractor = VectorFeatureExtractor()

    def test_demo_ward_polygons_validity(self):
        gdf = self.boundary_mgr.create_demo_ward_polygons("Kolkata")
        self.assertGreaterEqual(len(gdf), 5)
        self.assertTrue(all(gdf["geometry"].is_valid))
        self.assertTrue(all(gdf["area_m2"] > 0.0))
        self.assertEqual(gdf.crs.to_string(), "EPSG:4326")

    def test_zonal_statistics(self):
        data = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
        mask = np.array([[True, True, False], [True, True, False], [False, False, False]])
        stats = compute_zonal_statistics(data, mask=mask)
        self.assertEqual(stats["count"], 4)
        self.assertAlmostEqual(stats["mean"], 0.3, delta=0.01)

    def test_inverse_distance_weighting(self):
        stations = pd.DataFrame([
            {"station_id": "S1", "lat": 22.50, "lon": 88.30, "temperature_c": 35.0},
            {"station_id": "S2", "lat": 22.70, "lon": 88.50, "temperature_c": 40.0},
        ])
        res = self.weather_mapper.map_inverse_distance_weighting("W_TEST", 22.501, 88.301, stations, ["temperature_c"])
        self.assertAlmostEqual(res["temperature_c"], 35.0, delta=0.5)

    def test_construction_exposure_index(self):
        cei = self.vector_extractor.compute_construction_exposure_index(
            construction_density=5.0, outdoor_worker_density=2500.0, max_construction_density=10.0, max_worker_density=5000.0
        )
        self.assertAlmostEqual(cei, 0.5, delta=0.01)


if __name__ == "__main__":
    unittest.main()
