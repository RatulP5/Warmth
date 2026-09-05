"""Multi-Horizon Temporal Fusion Architecture.

Implements multi-horizon forecasting (D+1 ... D+5) over historical lookback windows (14 days),
static ward features, and known future numerical weather forecasts.
"""

import pickle
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.multioutput import MultiOutputRegressor


class TemporalFusionPredictor:
    """Multi-horizon sequential model forecasting across D+1 to D+5."""

    def __init__(
        self,
        lookback_days: int = 14,
        forecast_horizon_days: int = 5,
        hidden_dim: int = 64,
        random_state: int = 42,
    ):
        self.lookback_days = lookback_days
        self.forecast_horizon_days = forecast_horizon_days
        self.hidden_dim = hidden_dim
        self.random_state = random_state
        self.model: Optional[MultiOutputRegressor] = None

    def _flatten_inputs(self, X_past: np.ndarray, X_future: np.ndarray, X_static: np.ndarray) -> np.ndarray:
        n = len(X_past)
        return np.hstack([X_past.reshape(n, -1), X_future.reshape(n, -1), X_static.reshape(n, -1)])

    def fit(
        self,
        X_past_train: np.ndarray,
        X_future_train: np.ndarray,
        X_static_train: np.ndarray,
        y_train: np.ndarray,
        X_past_val: Optional[np.ndarray] = None,
        X_future_val: Optional[np.ndarray] = None,
        X_static_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> "TemporalFusionPredictor":
        X_train_flat = self._flatten_inputs(X_past_train, X_future_train, X_static_train)
        base = MLPRegressor(
            hidden_layer_sizes=(self.hidden_dim, self.hidden_dim // 2),
            activation="relu",
            max_iter=300,
            early_stopping=True,
            random_state=self.random_state,
        )
        self.model = MultiOutputRegressor(base)
        self.model.fit(X_train_flat, y_train)
        return self

    def predict(self, X_past: np.ndarray, X_future: np.ndarray, X_static: np.ndarray) -> np.ndarray:
        X_flat = self._flatten_inputs(X_past, X_future, X_static)
        return np.maximum(0.0, self.model.predict(X_flat))

    def save(self, filepath: str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {"model": self.model, "lookback": self.lookback_days, "horizon": self.forecast_horizon_days}, f
            )

    @classmethod
    def load(cls, filepath: str) -> "TemporalFusionPredictor":
        with open(filepath, "rb") as f:
            art = pickle.load(f)
        inst = cls(lookback_days=art["lookback"], forecast_horizon_days=art["horizon"])
        inst.model = art["model"]
        return inst
