"""
Converts empirical literature anchors into executable DLNM parameter weights.
"""
import json
import numpy as np
import variables as v

def calibrate():
    # 1. Daily Baseline Expected Deaths (Y_0)
    # Formula from Section 2.2 (Page 8): (Population * (CDR / 1000)) / 365.25
    baseline_daily_deaths = (
        v.POPULATION_2011 * (v.ANNUAL_CRUDE_DEATH_RATE_PER_1K / 1000.0)
    ) / 365.25

    # 2. Fit Polynomial Exposure Basis (beta_1, beta_2)
    # ln(RR) = b1 * delta_T + b2 * (delta_T^2)
    p1 = v.EXPOSURE_ANCHORS[1]
    p2 = v.EXPOSURE_ANCHORS[2]

    dt1 = p1["t_max"] - v.MMT_HOT_SEASON_TMAX
    dt2 = p2["t_max"] - v.MMT_HOT_SEASON_TMAX

    X = np.array([
        [dt1, dt1**2],
        [dt2, dt2**2]
    ])
    y = np.array([np.log(p1["rr"]), np.log(p2["rr"])])
    betas = np.linalg.solve(X, y)

    # 3. Lag Basis Decay Weights (Lags 0 to 3)
    # Heat shocks decay rapidly over 72 hours
    lags = np.arange(v.MAX_LAG_DAYS + 1)
    lambda_decay = 0.65
    raw_weights = np.exp(-lambda_decay * lags)
    norm_weights = (raw_weights / np.sum(raw_weights)).tolist()

    checkpoint = {
        "metadata": {
            "source": "Dholakia et al. (2015) CEEW-IITG-IIMA Study",
            "city": "Kolkata",
            "climate_zone": v.CLIMATE_ZONE
        },
        "parameters": {
            "mmt_celsius": v.MMT_HOT_SEASON_TMAX,
            "beta_1": float(round(betas[0], 6)),
            "beta_2": float(round(betas[1], 6)),
            "lag_weights": [float(round(w, 4)) for w in norm_weights],
            "baseline_daily_deaths": float(round(baseline_daily_deaths, 2))
        }
    }

    with open("kolkata_dlnm_params.json", "w") as f:
        json.dump(checkpoint, f, indent=4)

    return checkpoint

if __name__ == "__main__":
    calibrate()
    print("Parameters generated in kolkata_dlnm_params.json")