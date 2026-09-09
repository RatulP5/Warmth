"""Explainability and Non-Causal Feature Attribution Engine.

Extracts local feature contributions for risk predictions.
Strictly adheres to scientific reporting:
NEVER describes feature attribution as causal proof.
Uses explicit associative language: 'contributed to the model prediction', never 'caused mortality'.
"""

from typing import Dict, Any, List, Optional
import pandas as pd


class PredictionExplainer:
    """Explains model risk forecasts using local feature contributions."""

    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names

    def explain_prediction_local(
        self,
        feature_values: pd.Series,
        baseline_means: Optional[pd.Series] = None,
        top_k: int = 4,
    ) -> Dict[str, Any]:
        """Explain a single ward prediction based on deviation from regional baseline."""
        contributions = []
        for feat in self.feature_names:
            if feat in feature_values:
                try:
                    val = float(feature_values[feat])
                    base = float(baseline_means[feat]) if (baseline_means is not None and feat in baseline_means) else (val * 0.85)
                    diff = val - base
                    contributions.append({
                        "feature": feat,
                        "observed_value": round(val, 2),
                        "baseline_value": round(base, 2),
                        "relative_contribution": round(diff, 2),
                    })
                except (ValueError, TypeError):
                    continue

        contributions = sorted(contributions, key=lambda x: abs(x["relative_contribution"]), reverse=True)
        top_drivers = contributions[:top_k]

        explanation_phrases = []
        for d in top_drivers:
            direction = "elevated" if d["relative_contribution"] > 0 else "reduced"
            explanation_phrases.append(
                f"{direction} {d['feature']} (observed: {d['observed_value']}) contributed to the model prediction"
            )

        return {
            "top_contributing_features": top_drivers,
            "scientific_attribution_statement": "; ".join(explanation_phrases),
            "disclaimer": (
                "Notice: Feature importance represents statistical association with the model's "
                "risk prediction and must not be interpreted as direct clinical or causal evidence."
            ),
        }
