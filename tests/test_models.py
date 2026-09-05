"""Unit tests for ML Models, Conformal Uncertainty, and Multi-Horizon Temporal Predictor."""

import unittest
import numpy as np
import pandas as pd

from models.baselines import LightGBMHealthBaseline, XGBoostHealthBaseline
from models.uncertainty import ConformalPredictor
from models.temporal import TemporalFusionPredictor


class TestModelArchitectures(unittest.TestCase):
    def test_lightgbm_poisson_fit_and_predict(self):
        np.random.seed(42)
        n = 100
        X = pd.DataFrame({
            "peak_wbgt_c": np.random.uniform(25.0, 36.0, n),
            "min_night_temp_c": np.random.uniform(22.0, 32.0, n),
            "population_density": np.random.uniform(5000, 25000, n),
        })
        y = pd.Series(np.random.poisson(40, n))

        model = LightGBMHealthBaseline(objective="poisson", n_estimators=20)
        model.fit(X, y)
        preds = model.predict(X)
        self.assertEqual(len(preds), n)
        self.assertTrue(np.all(preds >= 0.0))

    def test_conformal_prediction_intervals(self):
        y_val = np.array([40.0, 50.0, 60.0, 45.0, 55.0])
        y_val_pred = np.array([42.0, 48.0, 58.0, 46.0, 53.0])
        cp = ConformalPredictor(confidence_level=0.80)
        cp.calibrate(y_val, y_val_pred)
        lower, upper = cp.predict_intervals(np.array([50.0]))
        self.assertLessEqual(lower[0], 50.0)
        self.assertGreaterEqual(upper[0], 50.0)

    def test_temporal_fusion_multi_horizon(self):
        n, lookback, horizon = 20, 14, 5
        X_past = np.random.randn(n, lookback, 4).astype(np.float32)
        X_future = np.random.randn(n, horizon, 3).astype(np.float32)
        X_static = np.random.randn(n, 5).astype(np.float32)
        y = np.random.uniform(10.0, 50.0, (n, horizon)).astype(np.float32)

        tft = TemporalFusionPredictor(lookback_days=lookback, forecast_horizon_days=horizon, hidden_dim=16)
        tft.fit(X_past, X_future, X_static, y)
        preds = tft.predict(X_past, X_future, X_static)
        self.assertEqual(preds.shape, (n, horizon))


if __name__ == "__main__":
    unittest.main()
