"""Unified Risk Fusion, Alert Classification, and Municipal Interventions Engine.

Combines:
1. Configurable risk tier definitions (NORMAL, WATCH, HIGH, SEVERE, EXTREME)
2. Quantitative health surge risk scoring
3. Rule-based municipal interventions (labor bans, hydration stations, misting tankers)
"""

from pathlib import Path
from typing import Dict, Any, List, Union, Optional
import yaml


def load_risk_thresholds(config_path: Union[str, Path] = "configs/config.yaml") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        path = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("risk", {}).get("levels", {})


class RiskScoringEngine:
    """Classifies risk trajectories based on configuration thresholds."""

    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        self.levels = thresholds or load_risk_thresholds()

    def classify_surge_risk(self, surge_percentage: float) -> Dict[str, Any]:
        val = max(0.0, float(surge_percentage))
        for level_name, props in self.levels.items():
            if props["min_surge_pct"] <= val <= props["max_surge_pct"]:
                return {
                    "risk_tier": level_name,
                    "color": props.get("color", "GREEN"),
                    "action_code": props.get("action_code", "ROUTINE"),
                    "surge_percentage": round(val, 1),
                }
        return {
            "risk_tier": "EXTREME",
            "color": "DARK_RED",
            "action_code": "CRITICAL_EMERGENCY_FULL_CIVIC_MOBILIZATION",
            "surge_percentage": round(val, 1),
        }


class InterventionRulesEngine:
    """Recommends targeted municipal interventions based on local risk and vulnerability."""

    def recommend_interventions(
        self,
        ward_id: str,
        risk_tier: str,
        predicted_surge_pct: float,
        ward_features: Dict[str, Any],
        is_night_recovery_deficit: bool = False,
    ) -> Dict[str, Any]:
        actions: List[str] = []
        protocols: List[str] = []

        outdoor_workers = ward_features.get("outdoor_worker_density", 0.0)
        elderly_pct = ward_features.get("elderly_percentage", 0.0)
        slum_pct = ward_features.get("slum_percentage", 0.0)
        tin_roofs = ward_features.get("tin_roofs_count", 0)

        if risk_tier in ["SEVERE", "EXTREME"]:
            actions.append("Mandate 11:00-16:00 outdoor construction and manual labor halt under disaster management act.")
            actions.append("Pre-alert emergency departments and mobilize backup paramedic response for heat-stroke.")
            actions.append("Deploy municipal water tankers and high-pressure mobile misting systems along transit hubs.")
            protocols.append("DISASTER_MANAGEMENT_TIER_1")
        elif risk_tier == "HIGH":
            actions.append("Activate shaded hydration posts with oral rehydration solution (ORS) at busy transit corridors.")
            actions.append("Issue high-heat occupational advisories to construction employers and gig delivery platforms.")
            actions.append("Alert Urban Primary Health Centers (UPHCs) to prepare dedicated heat-stroke stabilization beds.")
            protocols.append("MUNICIPAL_ALERT_TIER_2")
        elif risk_tier == "WATCH":
            actions.append("Broadcast public hydration and thermal safety advisories via community radio and local media.")
            actions.append("Ensure continuous municipal drinking water supply in public markets.")
            protocols.append("PUBLIC_ADVISORY_TIER_3")
        else:
            actions.append("Maintain routine public health surveillance and water distribution.")
            protocols.append("ROUTINE_MONITORING")

        if outdoor_workers >= 2500.0 and risk_tier in ["HIGH", "SEVERE", "EXTREME"]:
            actions.append(f"High outdoor labor ({outdoor_workers}/km²): Deploy mobile hydration vans directly to active work zones.")
        if elderly_pct >= 12.0 and risk_tier in ["HIGH", "SEVERE", "EXTREME"]:
            actions.append(f"Elevated senior population ({elderly_pct}%): Dispatch community health workers (ASHA/ANM) for wellness visits.")
        if slum_pct >= 25.0 and risk_tier in ["HIGH", "SEVERE", "EXTREME"]:
            actions.append(f"High slum settlement density ({slum_pct}%): Activate air-cooled community centers as public relief shelters.")
        if tin_roofs >= 40 and risk_tier in ["HIGH", "SEVERE", "EXTREME"]:
            actions.append("High concentration of heat-absorbing tin roofs: Priority target for cool-roof reflective paint initiatives.")
        if is_night_recovery_deficit:
            actions.append("CRITICAL NOCTURNAL DEFICIT: Night temperature >= 28°C prevents recovery. Keep public parks accessible overnight.")

        return {
            "ward_id": ward_id,
            "risk_tier": risk_tier,
            "predicted_surge_pct": round(predicted_surge_pct, 1),
            "triggered_protocols": protocols,
            "recommended_actions": actions,
        }
