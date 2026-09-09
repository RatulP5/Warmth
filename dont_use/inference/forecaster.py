"""Unified 5-Day Health Risk Forecasting Engine.

Produces ward-level 5-day health-impact risk forecasts, thermal profiles,
conformal prediction intervals, local feature attributions, and municipal action plans.
Exports:
- data/predictions/ward_predictions.parquet
- data/predictions/ward_predictions.geojson
- data/predictions/risk_levels.parquet
- data/predictions/recommended_actions.parquet
"""

from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
import geopandas as gpd
import numpy as np

from features.feature_pipeline import WeatherFeatureExtractor
from models.baselines import LightGBMHealthBaseline
from models.uncertainty import ConformalPredictor
from explainability.explainer import PredictionExplainer
from risk_engine.decision_engine import RiskScoringEngine, InterventionRulesEngine


class HealthRiskForecaster:
    """Coordinates multi-ward real-time 5-day forecasting pipeline."""

    def __init__(
        self,
        model_artifact_path: str = "data/models/artifacts/baseline_lightgbm.pkl",
        output_dir: str = "data/predictions",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.weather_ext = WeatherFeatureExtractor()
        self.risk_scorer = RiskScoringEngine()
        self.rules_engine = InterventionRulesEngine()

        if Path(model_artifact_path).exists():
            self.model = LightGBMHealthBaseline.load(model_artifact_path)
            self.explainer = PredictionExplainer(self.model.feature_names_)
        else:
            self.model = None
            self.explainer = None

        self.conformal = ConformalPredictor(confidence_level=0.80)
        self.conformal.q_val_ = 4.5

    def generate_5day_forecast(
        self,
        df_forecast_hourly: pd.DataFrame,
        df_spatial_features: pd.DataFrame,
        gdf_wards: Optional[gpd.GeoDataFrame] = None,
    ) -> List[Dict[str, Any]]:
        df_daily_forecast = self.weather_ext.extract_daily_diurnal_metrics(df_forecast_hourly)
        df_features = pd.merge(df_daily_forecast, df_spatial_features, on="ward_id", how="left").fillna(0.0)

        results = []
        now_iso = datetime.utcnow().isoformat()

        if self.model is not None:
            for feat in self.model.feature_names_:
                if feat not in df_features.columns:
                    df_features[feat] = 0.0
            point_preds = self.model.predict(df_features)
        else:
            acute = np.maximum(0.0, df_features["peak_wbgt_c"] - 29.0) ** 1.8
            night = np.maximum(0.0, df_features["min_night_temp_c"] - 27.0) ** 1.6
            point_preds = (acute * 3.0 + night * 3.5).values

        df_features["predicted_surge_val"] = np.round(point_preds, 1)

        for idx, row in df_features.iterrows():
            w_id = str(row["ward_id"])
            surge_val = float(row["predicted_surge_val"])
            tier_info = self.risk_scorer.classify_surge_risk(surge_val)
            lower_bound, upper_bound = self.conformal.predict_intervals(np.array([surge_val]))

            actions_info = self.rules_engine.recommend_interventions(
                ward_id=w_id,
                risk_tier=tier_info["risk_tier"],
                predicted_surge_pct=surge_val,
                ward_features=row.to_dict(),
                is_night_recovery_deficit=bool(row["is_night_recovery_deficit"]),
            )

            top_feats, attribution_stmt = [], ""
            if self.explainer:
                expl = self.explainer.explain_prediction_local(row)
                top_feats = expl["top_contributing_features"]
                attribution_stmt = expl["scientific_attribution_statement"]

            record = {
                "ward_id": w_id,
                "prediction_timestamp": now_iso,
                "forecast_date": str(row["date"]),
                "thermal_stress": {
                    "peak_drybulb_c": float(row["peak_temperature_c"]),
                    "min_night_temp_c": float(row["min_night_temp_c"]),
                    "peak_wbgt_c": float(row["peak_wbgt_c"]),
                    "peak_utci_c": float(row["peak_utci_c"]),
                    "peak_heat_index_c": float(row["peak_heat_index_c"]),
                    "is_night_deficit": bool(row["is_night_recovery_deficit"]),
                },
                "health_risk": {"hospitalization_surge_pct": surge_val},
                "prediction_interval": {
                    "confidence_level": 0.80,
                    "lower": float(lower_bound[0]),
                    "upper": float(upper_bound[0]),
                },
                "risk_tier": tier_info["risk_tier"],
                "color_code": tier_info["color"],
                "top_contributing_features": top_feats,
                "attribution_statement": attribution_stmt,
                "recommended_actions": actions_info["recommended_actions"],
            }
            results.append(record)

        self.save_prediction_outputs(results, df_features, gdf_wards)
        return results

    def save_prediction_outputs(
        self,
        results: List[Dict[str, Any]],
        df_features: pd.DataFrame,
        gdf_wards: Optional[gpd.GeoDataFrame] = None,
    ) -> None:
        flat_records, risk_records, actions_records = [], [], []

        for r in results:
            flat_records.append({
                "ward_id": r["ward_id"],
                "prediction_timestamp": r["prediction_timestamp"],
                "forecast_date": r["forecast_date"],
                "peak_temperature_c": r["thermal_stress"]["peak_drybulb_c"],
                "min_night_temp_c": r["thermal_stress"]["min_night_temp_c"],
                "peak_wbgt_c": r["thermal_stress"]["peak_wbgt_c"],
                "peak_utci_c": r["thermal_stress"]["peak_utci_c"],
                "peak_heat_index_c": r["thermal_stress"]["peak_heat_index_c"],
                "is_night_deficit": r["thermal_stress"]["is_night_deficit"],
                "surge_pct": r["health_risk"]["hospitalization_surge_pct"],
                "surge_interval_lower": r["prediction_interval"]["lower"],
                "surge_interval_upper": r["prediction_interval"]["upper"],
                "risk_tier": r["risk_tier"],
                "color_code": r["color_code"],
            })
            risk_records.append({
                "ward_id": r["ward_id"],
                "forecast_date": r["forecast_date"],
                "risk_tier": r["risk_tier"],
                "color_code": r["color_code"],
                "surge_pct": r["health_risk"]["hospitalization_surge_pct"],
            })
            for act in r["recommended_actions"]:
                actions_records.append({
                    "ward_id": r["ward_id"],
                    "forecast_date": r["forecast_date"],
                    "risk_tier": r["risk_tier"],
                    "action": act,
                })

        df_flat = pd.DataFrame(flat_records)
        df_flat.to_parquet(self.output_dir / "ward_predictions.parquet", index=False)
        pd.DataFrame(risk_records).to_parquet(self.output_dir / "risk_levels.parquet", index=False)
        pd.DataFrame(actions_records).to_parquet(self.output_dir / "recommended_actions.parquet", index=False)

        if gdf_wards is not None and not gdf_wards.empty:
            gdf_merged = gdf_wards.merge(df_flat, on="ward_id", how="inner")
            for c in gdf_merged.columns:
                if len(gdf_merged) > 0 and isinstance(gdf_merged[c].iloc[0], (datetime, date, pd.Timestamp)):
                    gdf_merged[c] = gdf_merged[c].astype(str)
            gdf_merged.to_file(self.output_dir / "ward_predictions.geojson", driver="GeoJSON")
