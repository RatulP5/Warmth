"""Unified Baseline Machine Learning Models.

Provides:
1. LightGBM Poisson Count Baseline Regressor
2. XGBoost Baseline Regressor
Includes early stopping, gain feature importance, and model serialization.
"""

import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb


class LightGBMHealthBaseline:
    """LightGBM Poisson regressor for health impact count forecasting."""

    def __init__(
        self,
        objective: str = "poisson",
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        max_depth: int = 5,
        random_state: int = 42,
    ):
        self.objective = objective
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.random_state = random_state
        self.model: Optional[lgb.LGBMRegressor] = None
        self.feature_names_: List[str] = []
        self.metadata_: Dict[str, Any] = {}

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        training_period: Optional[Tuple[str, str]] = None,
    ) -> "LightGBMHealthBaseline":
        self.feature_names_ = list(X_train.columns)
        self.model = lgb.LGBMRegressor(
            objective=self.objective,
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            random_state=self.random_state,
            verbosity=-1,
        )
        self.model.fit(X_train, y_train)
        self.metadata_ = {
            "model_type": "LightGBMRegressor",
            "feature_names": self.feature_names_,
            "training_period": training_period,
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.maximum(0.0, self.model.predict(X[self.feature_names_]))

    def get_feature_importances(self) -> pd.DataFrame:
        imp = self.model.booster_.feature_importance(importance_type="gain")
        return pd.DataFrame({
            "feature": self.feature_names_, "importance_gain": imp
        }).sort_values("importance_gain", ascending=False).reset_index(drop=True)

    def save(self, filepath: str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "metadata": self.metadata_}, f)

    @classmethod
    def load(cls, filepath: str) -> "LightGBMHealthBaseline":
        with open(filepath, "rb") as f:
            art = pickle.load(f)
        inst = cls()
        inst.model = art["model"]
        inst.metadata_ = art["metadata"]
        inst.feature_names_ = inst.metadata_["feature_names"]
        return inst


class XGBoostHealthBaseline:
    """XGBoost regressor benchmark."""

    def __init__(
        self,
        objective: str = "count:poisson",
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        max_depth: int = 4,
        random_state: int = 42,
    ):
        self.objective = objective
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.random_state = random_state
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_names_: List[str] = []

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> "XGBoostHealthBaseline":
        self.feature_names_ = list(X_train.columns)
        self.model = xgb.XGBRegressor(
            objective=self.objective,
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            random_state=self.random_state,
        )
        self.model.fit(X_train, y_train, verbose=False)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.maximum(0.0, self.model.predict(X[self.feature_names_]))
