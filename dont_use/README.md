# Extreme Heatwave Early Warning and Human Thermal Stress Index

A Python-only, research-grade and hackathon-executable scientific, geospatial, and machine learning pipeline for the Smart India Hackathon (MoES) problem statement: **"Extreme Heatwave Early Warning and Human Thermal Stress Index"**.

The system converts localized numerical weather forecasts, satellite imagery (Sentinel-2, Landsat 8/9, ESA WorldCover), OpenStreetMap urban morphology, demographic vulnerability, and historical public-health outcomes into **ward-level biophysical thermal stress indices and 3–5 day emergency hospitalization / mortality risk forecasts**.

---

## Mission & Architectural Scope

This repository contains **strictly Python-side intelligence, geospatial processing, ML pipelines, and offline CLI entrypoints**:
- Ingestion connectors & adapters (Open-Meteo, Copernicus Sentinel-2, Landsat TIRS, ESA WorldCover, OpenStreetMap Overpass, Census, Health registers)
- Data validation, quality auditing (`data_quality_report.json`), and schema enforcement
- Geospatial feature engineering (ward polygon boundaries, metric area projections in UTM, zonal statistics, weather-to-ward IDW / bilinear interpolation)
- Deterministic biophysical thermal stress engines (Outdoor & Indoor WBGT via Stull psychrometrics, UTCI, NOAA Heat Index)
- Temporal feature engineering (historical lags, multi-day rolling windows, consecutive hot day streaks) with **strict data-leakage prevention**
- Machine learning models (LightGBM Poisson count baseline, XGBoost, and Multi-Horizon Temporal Fusion Predictor for $D+1 \dots D+5$)
- Uncertainty quantification (Split Conformal Prediction intervals at 80% confidence, Brier score, ECE calibration)
- Explainability & feature attribution (non-causal associative driver ranking)
- Municipal risk fusion & intervention engine (color-coded alert tiers, labor restrictions, hydration posts, misting tanker deployments)
- Standardized Parquet, GeoParquet, and GeoJSON prediction outputs for consumption by external UI and visualization platforms.

> **Scope Restriction**: In adherence to `AGENTS.md`, this codebase intentionally contains **no frontend code** (React, Next.js, HTML/CSS), **no REST APIs** (FastAPI, Flask, Express), **no authentication**, and **no notification dispatch integrations**.

---

## Mathematical & Biophysical Formulations

### 1. Natural Wet-Bulb Temperature ($T_{\text{nw}}$)
Stull (2011) psychrometric formulation from ambient dry-bulb temperature ($T_a$, °C) and relative humidity ($RH$, %):
$$T_{\text{nw}} = T_a \arctan(0.151977 \sqrt{RH + 8.313659}) + \arctan(T_a + RH) - \arctan(RH - 1.676331) + 0.00391838 \, RH^{1.5} \arctan(0.023101 \, RH) - 4.686035$$

### 2. Black Globe Temperature ($T_g$)
Radiant solar flux and convective wind dissipation:
$$T_g = T_a + \frac{0.05 \cdot S}{v_{10} + 0.5}$$
where $S$ is downward solar irradiance ($\text{W/m}^2$) and $v_{10}$ is wind speed at 10m height ($\text{m/s}$).

### 3. Outdoor Wet-Bulb Globe Temperature (WBGT)
Standard ISO 7243 formulation:
$$\text{WBGT}_{\text{outdoor}} = 0.7 \cdot T_{\text{nw}} + 0.2 \cdot T_g + 0.1 \cdot T_a$$

### 4. Nocturnal Recovery Deficit
Minimum nighttime temperature between 22:00 and 05:00:
$$T_{\min} \ge 28.0^\circ\text{C}$$
Breaching this threshold indicates sustained failure of nocturnal cardiovascular thermoregulatory recovery.

### 5. Heat Vulnerability Index (HVI)
$$\text{HVI} = \frac{1.5 \cdot \text{tin\_roofs} + 2.0 \cdot \text{construction} + 0.05 \cdot \text{buildings}}{10 \cdot \max(1, \text{cooling\_buffers}) + 1}$$

---

## Directory Structure

```text
d:\Warmth/
├── configs/
│   └── config.yaml             # Unified configuration (data sources, features, thermal, models, paths)
├── data/
│   ├── raw/                    # Immutable raw downloads (weather, osm, satellite)
│   ├── features/               # Processed feature tables (Parquet) and sequence NPZ
│   ├── models/artifacts/       # Serialized models with complete training metadata
│   ├── predictions/            # Deliverables: predictions.parquet, geojson, interventions
│   ├── reports/                # Machine-readable data_quality_report.json
│   └── demo/                   # Verified offline pilot datasets & generator script
├── ingestion/
│   ├── weather.py              # Open-Meteo archive & live forecast adapters
│   ├── satellite.py            # Sentinel-2 NDVI, Landsat LST, WorldCover processors
│   ├── osm.py                  # Overpass API client with microclimate fallback zones
│   └── health_and_census.py    # Census demographics & health outcome loaders (NaN-preserving)
├── validation/
│   └── validator.py            # Pydantic schemas, quality auditing, missing flags, anomaly detection
├── geospatial/
│   ├── boundaries.py           # Ward geometry validation, UTM projections, weather-to-ward interpolation
│   └── spatial_features.py     # Zonal statistics, raster features, OSM morphology & construction index
├── thermal/
│   └── biophysics.py           # Unified Stull wet-bulb, globe temp, WBGT, UTCI, Heat Index, categories
├── features/
│   └── feature_pipeline.py     # Weather diurnal metrics, temporal lags/streaks, HVI, master assembly
├── datasets/
│   └── dataset_builder.py      # Chronological splits, multi-horizon 3D sequences (L=14, H=5), export
├── models/
│   ├── baselines.py            # LightGBM (Poisson) and XGBoost regressors
│   ├── temporal.py             # Multi-Horizon Temporal Fusion Predictor (D+1 ... D+5)
│   └── uncertainty.py          # Split Conformal Prediction intervals (80%) & ECE calibration
├── training/
│   └── trainer.py              # Baseline & temporal model training harnesses, metrics evaluation
├── inference/
│   └── forecaster.py           # Real-time 5-day forecasting, municipal risk fusion, GeoJSON export
├── explainability/
│   └── explainer.py            # Non-causal feature attribution and driver ranking
├── risk_engine/
│   └── decision_engine.py      # Risk scoring (NORMAL to EXTREME) and actionable municipal protocols
├── pipeline.py                 # Master CLI runner (spatial, dataset, train, forecast, run-all)
├── tests/                      # Consolidated automated unit and integration test suites
│   ├── test_thermal.py         # Thermodynamic and psychrometric benchmarks
│   ├── test_geospatial.py      # Coordinate projections and zonal stats
│   ├── test_features.py        # Lags, rolling windows, and leakage checks
│   └── test_models.py          # LightGBM, Conformal intervals, and Multi-Horizon Predictor
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Build packaging
├── DATA_SOURCES.md             # Dataset provenance, resolution, and licenses
└── MODEL_CARD.md               # Model details, inputs, evaluation, and ethics
```

---

## Installation

Ensure Python 3.11+ is installed.

```bash
# Clone or navigate to the repository
cd d:\Warmth

# Install dependencies
pip install -r requirements.txt
```

---

## Running the Platform

### 1. Run Complete Pipeline End-to-End (`--demo` Mode)
To exercise the entire pipeline offline with verified synthetic data layers:
```bash
python pipeline.py run-all --demo
```
This executes all 5 stages in sequence:
1. Generates pilot datasets in `data/demo/` (Kolkata microclimates)
2. Runs automated data quality audits -> `data/reports/data_quality_report.json`
3. Extracts satellite raster and urban vector features -> `data/features/spatial_features.parquet`
4. Assembles unified training dataset and trains both LightGBM and Multi-Horizon models
5. Produces real-time 5-day risk predictions and municipal interventions -> `data/predictions/`

### 2. Independent Modular CLI Entrypoints
Each pipeline stage can also be executed independently via `pipeline.py`:

```bash
# Extract ward spatial features
python pipeline.py spatial --demo

# Build unified training dataset with chronological partitions
python pipeline.py dataset --demo

# Train baseline and temporal models
python pipeline.py train --demo

# Run real-time 5-day health risk forecast
python pipeline.py forecast --demo
```

### 3. Run Automated Tests
```bash
python -m pytest tests/
```

---

## Core Deliverables Generated

The final pipeline exports structured outputs ready for downstream consumption:
- `data/predictions/ward_predictions.parquet`: Full forecast table with diurnal weather, WBGT, UTCI, Heat Index, predicted surge %, and conformal 80% confidence intervals.
- `data/predictions/ward_predictions.geojson`: GeoJSON geometry file with embedded risk attributes for map layers.
- `data/predictions/risk_levels.parquet`: Ward-level risk classifications (`NORMAL`, `WATCH`, `HIGH`, `SEVERE`, `EXTREME`).
- `data/predictions/recommended_actions.parquet`: Specific municipal, labor, and medical interventions mapped to local ward vulnerability profiles.
- `data/reports/data_quality_report.json`: Automated data quality audit tracking missing data, ranges, and consistency flags.