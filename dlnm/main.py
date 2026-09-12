"""
main.py
Calculates day-wise lag breakdown and cumulative excess mortality.
"""
import os
import json
import numpy as np
from calibration import calibrate

class DLNMAnalyzer:
    def __init__(self, config_file="kolkata_dlnm_params.json"):
        if not os.path.exists(config_file):
            calibrate()
            
        with open(config_file) as f:
            cfg = json.load(f)["parameters"]

        self.mmt = cfg["mmt_celsius"]
        self.b1 = cfg["beta_1"]
        self.b2 = cfg["beta_2"]
        self.weights = cfg["lag_weights"]
        self.base_deaths = cfg["baseline_daily_deaths"]

    def evaluate_window(self, temps_window: list) -> dict:
        """
        temps_window: [T_today, T_yesterday, T_2days_ago, T_3days_ago]
        """
        lag_labels = [
            "Lag 0 (Today)",
            "Lag 1 (Yesterday)",
            "Lag 2 (2 Days Ago)",
            "Lag 3 (3 Days Ago)"
        ]

        daywise_results = []
        cumulative_log_rr = 0.0

        for i, (temp, weight, label) in enumerate(zip(temps_window, self.weights, lag_labels)):
            if temp > self.mmt:
                dt = temp - self.mmt
                # Day-specific log(RR) contribution weighted by lag decay
                log_rr_day = (self.b1 * dt + self.b2 * (dt ** 2)) * weight
                rr_day = float(np.exp(log_rr_day))
                excess_deaths_day = self.base_deaths * (rr_day - 1.0)
            else:
                log_rr_day = 0.0
                rr_day = 1.0
                excess_deaths_day = 0.0

            cumulative_log_rr += log_rr_day

            daywise_results.append({
                "day_label": label,
                "temperature_c": temp,
                "lag_weight": round(weight, 3),
                "relative_risk": round(rr_day, 4),
                "excess_deaths": round(excess_deaths_day, 1)
            })

        # Cumulative totals
        cum_rr = float(np.exp(cumulative_log_rr))
        total_excess_deaths = self.base_deaths * (cum_rr - 1.0) if cum_rr > 1.0 else 0.0
        pct_increase = (cum_rr - 1.0) * 100.0 if cum_rr > 1.0 else 0.0

        return {
            "daywise_breakdown": daywise_results,
            "cumulative_relative_risk": round(cum_rr, 4),
            "mortality_surge_pct": round(pct_increase, 2),
            "total_excess_deaths": round(total_excess_deaths, 1)
        }

def main():
    analyzer = DLNMAnalyzer()

    # Sustained heat spell in Kolkata: 41.0°C today, 40.5°C yesterday, 39.0°C, 38.0°C
    test_window = [26.0, 27.6, 25.4, 28.4]#[41.0, 40.5, 39.0, 38.0] 
    out = analyzer.evaluate_window(test_window)

    print("=" * 75)
    print("          KOLKATA HEAT-HEALTH DLNM: DAY-WISE LAG BREAKDOWN")
    print(f"          Baseline MMT: {analyzer.mmt}°C | Baseline Deaths/Day: {analyzer.base_deaths}")
    print("=" * 75)

    print(f"\n{'Lag Day':<22} | {'Temp (°C)':<10} | {'Weight':<8} | {'RR (Day)':<10} | {'Excess Deaths'}")
    print("-" * 75)

    for row in out["daywise_breakdown"]:
        print(f"{row['day_label']:<22} | {row['temperature_c']:<10} | {row['lag_weight']:<8} | {row['relative_risk']:<10} | ~{row['excess_deaths']} deaths")

    print("-" * 75)
    print(f"CUMULATIVE RELATIVE RISK (RR) : {out['cumulative_relative_risk']}")
    print(f"TOTAL MORTALITY SURGE         : +{out['mortality_surge_pct']}% above normal baseline")
    print(f"TOTAL ESTIMATED EXCESS DEATHS : ~{out['total_excess_deaths']} casualties across the window")
    print("=" * 75)

if __name__ == "__main__":
    main()