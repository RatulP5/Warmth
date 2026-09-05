"""Unit tests for Temporal and Feature Engineering Pipelines."""

import unittest
from datetime import date, timedelta
import numpy as np
import pandas as pd

from features.feature_pipeline import add_weather_lags, add_rolling_features, compute_consecutive_hot_days
from datasets.dataset_builder import ChronologicalSplitter, MultiHorizonSequenceBuilder


class TestFeatureEngineering(unittest.TestCase):
    def test_weather_lags_prevent_lookahead(self):
        df = pd.DataFrame({
            "ward_id": ["W1", "W1", "W1", "W1"],
            "timestamp": pd.date_range("2024-05-01 00:00", periods=4, freq="h"),
            "temperature_c": [30.0, 32.0, 34.0, 36.0],
        })
        df_lagged = add_weather_lags(df, value_cols=["temperature_c"], lag_steps=[1, 2])
        self.assertTrue(np.isnan(df_lagged["temperature_c_lag_1"].iloc[0]))
        self.assertEqual(df_lagged["temperature_c_lag_1"].iloc[1], 30.0)

    def test_rolling_features_shift(self):
        df = pd.DataFrame({
            "ward_id": ["W1"] * 5,
            "timestamp": pd.date_range("2024-05-01", periods=5, freq="D"),
            "temperature_c": [20.0, 30.0, 40.0, 50.0, 60.0],
        })
        df_roll = add_rolling_features(df, value_cols=["temperature_c"], windows=[2], time_col="timestamp")
        self.assertEqual(df_roll["temperature_c_rolling_2"].iloc[2], 25.0)

    def test_consecutive_hot_days_streak(self):
        df = pd.DataFrame({
            "ward_id": ["W1"] * 5,
            "date": [date(2024, 5, 1) + timedelta(days=i) for i in range(5)],
            "peak_temperature_c": [38.0, 41.0, 42.0, 43.0, 37.0],
            "peak_wbgt_c": [28.0, 31.0, 32.0, 31.0, 27.0],
        })
        df_streak = compute_consecutive_hot_days(df, temp_threshold_c=40.0)
        self.assertEqual(df_streak["consecutive_hot_days"].iloc[1], 0)
        self.assertEqual(df_streak["consecutive_hot_days"].iloc[2], 1)

    def test_chronological_ordering(self):
        dates = [date(2024, 4, 1) + timedelta(days=i) for i in range(100)]
        df = pd.DataFrame({"ward_id": ["W1"] * 100, "date": dates, "value": np.arange(100)})
        splitter = ChronologicalSplitter(time_col="date", val_ratio=0.15, test_ratio=0.15)
        df_train, df_val, df_test = splitter.split(df)
        self.assertLess(df_train["date"].max(), df_val["date"].min())
        self.assertLess(df_val["date"].max(), df_test["date"].min())


if __name__ == "__main__":
    unittest.main()
