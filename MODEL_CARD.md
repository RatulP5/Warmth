# Model Card — Heatwave Early Warning & Health Surge Engine

## Model Details
- **Architecture**:
  - Primary Benchmark: LightGBM Poisson Regressor with early stopping
  - Advanced Multi-Horizon Sequence Predictor: Temporal Fusion Predictor (Lookback $L=14$ days, Forecast Horizon $H=5$ days)
- **Version**: 1.0.0
- **Intended Use**: Operational early warning risk categorization and emergency hospital bed surge forecasting for municipal authorities and disaster management teams.
- **License**: Apache 2.0 / Open SIH Core

---

## Intended Domain & Target Task
At time $T$, predict all-cause emergency hospitalizations and mortality surges across $T+1, T+2, T+3, T+4, T+5$ days across urban municipal wards.
- **Primary Target**: Daily emergency room admissions (`emergency_hospitalizations`)
- **Secondary Target**: All-cause daily mortality (`all_cause_mortality`)
- **Spatial Granularity**: Administrative Ward (`ward_id`)
- **Temporal Granularity**: Daily diurnal metrics aggregated from hourly numerical forecasts

---

## Training Data & Inputs

### 1. Static Ward Features
- **Socio-Demographic Vulnerability**: Population density ($pop/km^2$), elderly share (% $\ge 65$ yrs), child share (% $\le 5$ yrs), outdoor worker density ($workers/km^2$), slum household share (%).
- **Urban Morphology**: Building density ($buildings/km^2$), road density ($km/km^2$), construction site density ($sites/km^2$), cooling buffer count (parks, open water, urban canopy), tin roof count.
- **Satellite Zonal Baselines**: Sentinel-2 mean/median/p90 NDVI, vegetation percentage; Landsat 8/9 mean/p90 Land Surface Temperature (LST, °C); ESA WorldCover surface class fractions.

### 2. Historical Time-Varying Covariates (Past 14 Days)
- Daytime peak dry-bulb temperature ($T_a$, °C)
- Daytime peak Wet-Bulb Globe Temperature (WBGT, °C)
- Minimum nighttime temperature ($T_{\min}$, °C between 22:00 and 05:00)
- Nocturnal cardiovascular recovery deficit indicator ($T_{\min} \ge 28^\circ\text{C}$)
- Relative humidity (%), 10m wind speed ($m/s$), downward solar irradiance ($W/m^2$)
- Universal Thermal Climate Index (UTCI, °C) and NOAA Heat Index (°C)
- Historical health lags ($D-1, D-3, \text{rolling } 7D$)
- Heatwave spell streak counters (`consecutive_hot_days`, `consecutive_high_wbgt_days`)

### 3. Known Future Covariates ($D+1 \dots D+5$)
- Numerical weather forecasts only ($T_{a,\text{forecast}}$, $T_{\min,\text{forecast}}$, $\text{WBGT}_{\text{forecast}}$, $\text{RH}_{\text{forecast}}$).
- **Strict Leakage Rule**: Future observed weather and future target values are strictly barred from inference features.

---

## Validation Strategy
- **Partitioning Method**: Pure Chronological Walk-Forward Split (Train $\le$ 2024-05-13, Validation $\le$ 2024-05-22, Test $\le$ 2024-05-31).
- **Leakage Prevention Checklist**:
  1. No future target variables used in rolling features (strict `.shift(1)` enforced).
  2. No normalization statistics calculated across the entire dataset prior to splitting.
  3. Feature selection and baseline anomaly baselines derived strictly from past windows.

---

## Uncertainty & Calibration
- **Method**: Split Conformal Prediction.
- **Coverage Guarantee**: Non-parametric finite-sample coverage at $1 - \alpha = 0.80$ (80% empirical prediction intervals $[\hat{y} - q_{\text{val}}, \hat{y} + q_{\text{val}}]$).
- **Calibration Evaluation**: Expected Calibration Error (ECE) and Brier reliability scores across thresholded alert tiers.

---

## Explainability & Attribution
- **Method**: Local feature contribution analysis.
- **Scientific Standard**: Evaluates directional model drivers without asserting medical causation.
  - *Standard phrasing*: "Elevated peak WBGT contributed to the model prediction" (never "WBGT caused deaths").

---

## Operational Limitations & Ethical Safeguards
1. **Medical Diagnostic Non-equivalence**: Model outputs indicate aggregate municipal demand surge percentages and must not be used for individual clinical diagnoses or triage.
2. **Missing Record Integrity**: Unrecorded health data must remain flagged as missing (`NaN`); under no circumstances are missing entries converted to zero deaths.
3. **Microclimate Extrapolation**: Gridded weather models cannot resolve individual building shadows; ward-level morphological features (cooling buffers and tin roofs) act as spatial proxies.
