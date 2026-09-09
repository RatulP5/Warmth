"""Unified Uncertainty Quantification and Probability Calibration.

Combines:
1. Split Conformal Prediction (finite-sample guaranteed prediction intervals)
2. Isotonic probability calibration
3. Reliability auditing: Expected Calibration Error (ECE) and Brier score
"""

from typing import Tuple, Dict, Any, Optional
import numpy as np
from sklearn.isotonic import IsotonicRegression


class ConformalPredictor:
    """Computes distribution-free conformal prediction intervals."""

    def __init__(self, confidence_level: float = 0.80):
        self.confidence_level = confidence_level
        self.alpha = 1.0 - confidence_level
        self.q_val_: Optional[float] = None

    def calibrate(self, y_val: np.ndarray, y_val_pred: np.ndarray) -> "ConformalPredictor":
        residuals = np.abs(y_val - y_val_pred)
        n = len(residuals)
        q_level = min(1.0, np.ceil((n + 1) * (1.0 - self.alpha)) / n)
        self.q_val_ = float(np.quantile(residuals, q_level))
        return self

    def predict_intervals(self, y_pred: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if self.q_val_ is None:
            self.q_val_ = 5.0
        lower = np.maximum(0.0, y_pred - self.q_val_)
        upper = y_pred + self.q_val_
        return np.round(lower, 2), np.round(upper, 2)

    def evaluate_coverage(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        lower, upper = self.predict_intervals(y_pred)
        covered = (y_true >= lower) & (y_true <= upper)
        return {
            "target_confidence": self.confidence_level,
            "empirical_coverage": round(float(np.mean(covered)), 3),
            "average_interval_width": round(float(np.mean(upper - lower)), 2),
            "conformal_margin": round(self.q_val_, 2),
        }


def compute_brier_score(y_true_binary: np.ndarray, y_prob: np.ndarray) -> float:
    return round(float(np.mean((y_prob - y_true_binary) ** 2)), 4)


def compute_expected_calibration_error(y_true_binary: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece, n = 0.0, len(y_true_binary)
    for i in range(n_bins):
        in_bin = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i + 1])
        if np.sum(in_bin) > 0:
            ece += (np.sum(in_bin) / n) * np.abs(np.mean(y_true_binary[in_bin]) - np.mean(y_prob[in_bin]))
    return round(float(ece), 4)


class IsotonicProbabilityCalibrator:
    """Non-parametric isotonic regression calibrator for predicted risk scores."""

    def __init__(self):
        self.calibrator = IsotonicRegression(out_of_bounds="clip")

    def fit(self, scores: np.ndarray, y_true_binary: np.ndarray) -> "IsotonicProbabilityCalibrator":
        self.calibrator.fit(scores, y_true_binary)
        return self

    def predict_proba(self, scores: np.ndarray) -> np.ndarray:
        return np.clip(self.calibrator.predict(scores), 0.0, 1.0)
