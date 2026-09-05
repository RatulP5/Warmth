"""Unified Model Training and Evaluation Harness.

Combines:
1. Error metrics: MAE, RMSE, Poisson deviance, False Alarm Rate, Missed Event Rate
2. Training pipelines for LightGBM Poisson baseline and Temporal Fusion multi-horizon models
"""

from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from models.baselines import LightGBMHealthBaseline
from models.temporal import TemporalFusionPredictor
from models.uncertainty import ConformalPredictor


# ---------------------------------------------------------------------------
# 1. Evaluation Metrics
# ---------------------------------------------------------------------------

def compute_poisson_deviance(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-6) -> float:
    yt = np.maximum(eps, y_true)
    yp = np.maximum(eps, y_pred)
    return round(float(2.0 * np.mean(yt * np.log(yt / yp) - (yt - yp))), 4)


def evaluate_forecast_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "MAE": round(float(np.mean(np.abs(y_true - y_pred))), 3),
        "RMSE": round(float(np.sqrt(np.mean((y_true - y_pred) ** 2))), 3),
        "poisson_deviance": compute_poisson_deviance(y_true, y_pred),
    }


def evaluate_operational_alerts(y_true: np.ndarray, y_pred: np.ndarray, thresh: float = 20.0) -> Dict[str, float]:
    true_event = y_true >= thresh
    pred_event = y_pred >= thresh
    tp = np.sum(true_event & pred_event)
    fp = np.sum(~true_event & pred_event)
    fn = np.sum(true_event & ~pred_event)
    tn = np.sum(~true_event & ~pred_event)
    return {
        "precision": round(float(tp / (tp + fp)), 3) if (tp + fp) > 0 else 0.0,
        "recall": round(float(tp / (tp + fn)), 3) if (tp + fn) > 0 else 0.0,
        "false_alarm_rate": round(float(fp / (fp + tn)), 3) if (fp + tn) > 0 else 0.0,
        "missed_event_rate": round(float(fn / (tp + fn)), 3) if (tp + fn) > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# 2. Training Pipelines
# ---------------------------------------------------------------------------

def train_baseline_pipeline(
    train_path: str = "data/features/unified_dataset_train.parquet",
    val_path: str = "data/features/unified_dataset_val.parquet",
    test_path: str = "data/features/unified_dataset_test.parquet",
    model_output_path: str = "data/models/artifacts/baseline_lightgbm.pkl",
    target_col: str = "emergency_hospitalizations",
) -> Dict[str, Any]:
    """Train LightGBM Poisson baseline."""
    df_train = pd.read_parquet(train_path)
    df_val = pd.read_parquet(val_path)
    df_test = pd.read_parquet(test_path)

    ignore_cols = [
        "ward_id", "date", "timestamp", "spatial_id", "spatial_level",
        "all_cause_mortality", "emergency_hospitalizations", "heat_stroke_cases", "cardiovascular_admissions",
        "is_forecast",
    ]
    numeric_cols = df_train.select_dtypes(include=[np.number, bool]).columns
    feature_cols = [c for c in numeric_cols if c not in ignore_cols]

    train_clean = df_train.dropna(subset=[target_col])
    val_clean = df_val.dropna(subset=[target_col])
    test_clean = df_test.dropna(subset=[target_col])

    X_train, y_train = train_clean[feature_cols].fillna(0.0), train_clean[target_col]
    X_val, y_val = val_clean[feature_cols].fillna(0.0), val_clean[target_col]
    X_test, y_test = test_clean[feature_cols].fillna(0.0), test_clean[target_col]

    model = LightGBMHealthBaseline(objective="poisson", n_estimators=150, learning_rate=0.05)
    training_period = (str(df_train["date"].min()), str(df_train["date"].max()))
    model.fit(X_train, y_train, X_val, y_val, training_period=training_period)

    # Conformal interval calibration
    y_val_pred = model.predict(X_val)
    conformal = ConformalPredictor(confidence_level=0.80)
    conformal.calibrate(y_val.values, y_val_pred)

    y_test_pred = model.predict(X_test)
    test_metrics = evaluate_forecast_metrics(y_test.values, y_test_pred)
    coverage_audit = conformal.evaluate_coverage(y_test.values, y_test_pred)

    model.save(model_output_path)

    return {
        "model_type": "LightGBM Baseline (Poisson)",
        "features_used": feature_cols,
        "test_metrics": test_metrics,
        "uncertainty_audit": coverage_audit,
        "artifact_path": model_output_path,
    }


def train_temporal_pipeline(
    sequences_npz_path: str = "data/features/unified_dataset_sequences.npz",
    model_output_path: str = "data/models/artifacts/tft_model.pkl",
) -> Dict[str, Any]:
    """Train multi-horizon sequential model."""
    data = np.load(sequences_npz_path)
    X_train_past = data["X_train_past"]
    X_train_future = data["X_train_future"]
    X_train_static = data["X_train_static"]
    y_train = data["y_train"]

    X_test_past = data["X_test_past"]
    X_test_future = data["X_test_future"]
    X_test_static = data["X_test_static"]
    y_test = data["y_test"]

    model = TemporalFusionPredictor(lookback_days=14, forecast_horizon_days=5, hidden_dim=64)
    model.fit(X_train_past, X_train_future, X_train_static, y_train)

    y_test_pred = model.predict(X_test_past, X_test_future, X_test_static)
    horizon_metrics = {}
    for h in range(min(5, y_test.shape[1])):
        horizon_metrics[f"Day_{h+1}"] = evaluate_forecast_metrics(y_test[:, h], y_test_pred[:, h])

    model.save(model_output_path)
    return {
        "model_type": "Temporal Fusion Multi-Horizon Predictor",
        "horizon_metrics": horizon_metrics,
        "artifact_path": model_output_path,
    }
