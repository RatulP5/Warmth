"""Unit tests for Biophysical Thermal Stress Engine."""

import unittest
import numpy as np

from thermal.biophysics import (
    calculate_natural_wet_bulb,
    calculate_globe_temperature,
    calculate_outdoor_wbgt,
    calculate_indoor_wbgt,
    calculate_heat_index,
    calculate_utci,
    evaluate_nocturnal_recovery,
    categorize_wbgt,
    categorize_heat_index,
)


class TestThermalEngine(unittest.TestCase):
    def test_natural_wet_bulb_stull_bounds(self):
        tw_saturated = calculate_natural_wet_bulb(temperature_c=30.0, relative_humidity_pct=100.0)
        self.assertAlmostEqual(tw_saturated, 30.0, delta=1.0)

        tw_dry = calculate_natural_wet_bulb(temperature_c=35.0, relative_humidity_pct=20.0)
        self.assertTrue(18.0 <= tw_dry <= 22.0)

        t_arr = np.array([25.0, 30.0, 35.0])
        rh_arr = np.array([50.0, 60.0, 70.0])
        tw_arr = calculate_natural_wet_bulb(t_arr, rh_arr)
        self.assertEqual(len(tw_arr), 3)
        self.assertTrue(np.all(tw_arr <= t_arr + 0.1))

    def test_outdoor_wbgt_formula(self):
        t_air, rh, wind, solar = 35.0, 60.0, 2.0, 800.0
        wbgt = calculate_outdoor_wbgt(t_air, rh, wind, solar)
        self.assertGreater(wbgt, 28.0)

    def test_heat_index_noaa_benchmarks(self):
        hi_cool = calculate_heat_index(22.0, 50.0)
        self.assertAlmostEqual(hi_cool, 22.0, delta=2.0)

        hi_extreme = calculate_heat_index(38.0, 60.0)
        self.assertGreater(hi_extreme, 48.0)

    def test_utci_operational_bounds(self):
        utci_mild = calculate_utci(20.0, 50.0, 1.0, 100.0)
        self.assertTrue(15.0 <= utci_mild <= 26.0)

        utci_extreme = calculate_utci(42.0, 50.0, 0.8, 900.0)
        self.assertGreaterEqual(utci_extreme, 40.0)

    def test_thermal_categories_mapping(self):
        self.assertIn("Extreme", categorize_wbgt(35.5))
        self.assertIn("Normal", categorize_wbgt(24.0))
        self.assertIn("Extreme Danger", categorize_heat_index(54.0))

        nocturnal = evaluate_nocturnal_recovery(min_night_temp_c=29.2)
        self.assertTrue(nocturnal["is_recovery_deficit"])
        self.assertEqual(nocturnal["recovery_deficit_degrees_c"], 1.2)


if __name__ == "__main__":
    unittest.main()
