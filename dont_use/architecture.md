# Extreme Heatwave Early Warning and Human Thermal Stress Index

## Core AI / Data / Geospatial Architecture

> This document covers the **data, geospatial, thermal-stress, ML, forecasting, validation, and alert-decision layers only**. Frontend and application backend architecture are intentionally excluded.

---

## 1. Objective

Build an intelligence pipeline that transforms localized weather and environmental observations/forecasts into:

1. **Human Thermal Stress metrics** such as WBGT, UTCI, and Heat Index.
2. **Ward-level environmental and demographic vulnerability features** derived from actual geospatial data rather than hardcoded values.
3. **3–5 day mortality and hospitalization risk forecasts** where sufficiently granular health data are available.
4. **Hyper-local risk classifications and intervention triggers** for municipal/disaster-management use.
5. **Explainable and uncertainty-aware predictions** rather than unsupported point estimates.

The architecture follows the problem statement's emphasis on temperature, relative humidity, wind speed, solar radiation, historical public-health data, demographics, localized weather, 3–5 day health-impact forecasting, and ward/zone-level alerts.

---

# 2. High-Level Architecture

```text
                           EXTERNAL DATA SOURCES
                                   |
              +--------------------+--------------------+
              |                    |                    |
              v                    v                    v
       WEATHER / FORECAST      SATELLITE / GIS      HEALTH / DEMOGRAPHIC
              |                    |                    |
              +--------------------+--------------------+
                                   |
                                   v
                         DATA INGESTION LAYER
                                   |
                                   v
                        DATA QUALITY / HARMONIZATION
                                   |
                    +--------------+--------------+
                    |                             |
                    v                             v
             WEATHER DATA CUBE              GIS DATA LAYERS
             (time x lat x lon)             (ward polygons etc.)
                    |                             |
                    +--------------+--------------+
                                   |
                                   v
                        SPATIAL FEATURE ENGINE
                                   |
           +-----------------------+-----------------------+
           |                       |                       |
           v                       v                       v
      WEATHER FEATURES       ENVIRONMENTAL           VULNERABILITY
                             FEATURES                 FEATURES
           |                       |                       |
           +-----------------------+-----------------------+
                                   |
                                   v
                        THERMAL STRESS ENGINE
                     +-------------+-------------+
                     |             |             |
                     v             v             v
                    WBGT          UTCI       HEAT INDEX
                     |             |             |
                     +-------------+-------------+
                                   |
                                   v
                        TEMPORAL FEATURE ENGINE
                                   |
                                   v
                       HEALTH IMPACT ML PIPELINE
                    +--------------+--------------+
                    |                             |
                    v                             v
             MORTALITY RISK               HOSPITALIZATION RISK
                    |                             |
                    +--------------+--------------+
                                   |
                                   v
                         UNCERTAINTY / CALIBRATION
                                   |
                                   v
                        RISK FUSION / DECISION ENGINE
                                   |
                                   v
                      WARD-LEVEL RISK + INTERVENTION
                                   |
                                   v
                         STORED PREDICTION OUTPUTS
```

---

# 3. Design Principles

## 3.1 Do not hardcode ward characteristics

Ward-level properties such as greenery, built-up area, construction intensity, water coverage, and land-surface temperature must be **derived from spatial data**.

Example:

```text
Sentinel-2 imagery
        -> NDVI / vegetation
        -> zonal statistics
        -> Ward 17 vegetation_percentage
```

not:

```text
Ward 17 = 35% green  # hardcoded
```

## 3.2 Separate hazard from vulnerability

A ward's physical heat exposure is different from its population vulnerability.

```text
HAZARD
  = temperature + humidity + wind + radiation + thermal indices

VULNERABILITY
  = elderly + outdoor workers + population density + socioeconomic/environmental factors

HEALTH IMPACT
  = f(hazard, vulnerability, historical health outcomes)
```

## 3.3 Use ML where prediction is required, not where physics is already known

Do not train an ML model to rediscover WBGT/UTCI formulas.

```text
Physical / deterministic layer:
Weather -> WBGT / UTCI / Heat Index

Machine-learning layer:
Thermal stress + exposure + vulnerability + historical health
-> future health risk
```

## 3.4 Preserve temporal causality

Training data must not contain future information relative to the prediction timestamp.

For a D+3 forecast, only features available at time D may be used unless explicitly treated as forecast inputs.

---

# 4. Data Source Categories

## 4.1 Weather and Forecast Data

Required variables:

```text
- air_temperature
- relative_humidity
- wind_speed
- solar_radiation
```

Recommended variables:

```text
- dew_point
- surface_pressure
- cloud_cover
- precipitation
- wind_direction
- minimum_temperature
- maximum_temperature
- nighttime_temperature
```

Both historical observations and future forecasts are required.

### Data representation

Weather data should be stored as a multidimensional data cube:

```text
(time, latitude, longitude, variable)
```

Use **Xarray** for this representation.

---

## 4.2 Satellite / Earth Observation Data

Primary purpose: derive environmental features that affect localized thermal exposure.

Recommended layers:

```text
- NDVI
- vegetation fraction
- tree-cover estimate
- land-cover classes
- Land Surface Temperature (LST)
- water-body coverage
- built-up / impervious surface indicators
```

### Core products

**Sentinel-2**:

- vegetation and land-cover related features
- Red and NIR bands for NDVI
- high-resolution optical imagery

**Landsat / suitable LST products**:

- Land Surface Temperature
- urban heat-island / surface-heating analysis

**Copernicus land-cover products**:

- tree cover
- grassland
- built-up
- water and other land-cover classes

---

## 4.3 OpenStreetMap / GIS Features

Use GIS layers to derive human-exposure and urban-form features.

Potential OSM-derived layers:

```text
- buildings
- roads
- landuse
- construction sites
- water bodies
- hospitals
- schools
- other relevant public infrastructure
```

Construction is particularly important because it provides a proxy for potential outdoor-worker exposure.

Useful fields:

```text
construction_site_count
construction_area_m2
construction_density
major_road_length
road_density
building_count
building_area_m2
building_density
hospital_count
```

---

## 4.4 Census / Demographic Data

Required or strongly recommended variables:

```text
- total_population
- population_density
- elderly_population
- elderly_percentage
- children_population
- outdoor_worker_population
- outdoor_worker_percentage
```

Possible vulnerability variables:

```text
- socioeconomic indicators
- housing density
- slum-related population/household indicators
- electricity access
- water access
```

The exact spatial resolution must be preserved. Do not label district-level values as ward-level values.

---

## 4.5 Health Data

Preferred targets:

```text
- daily all-cause mortality
- heat-related mortality
- daily hospital admissions
- emergency visits
- heat-stroke cases
- dehydration cases
- cardiovascular admissions
- respiratory admissions
```

Minimum model target for a mortality model:

```text
location + date + death_count
```

Preferred granularity:

```text
ward/day
```

If only district/day or city/day health data are available, retain that resolution and train the health model at the resolution actually supported by the labels.

---

# 5. Data Ingestion Layer

## 5.1 Responsibilities

The ingestion layer should:

```text
1. Download/fetch source data.
2. Validate file/API responses.
3. Standardize variable names.
4. Normalize units.
5. Attach timestamps and spatial reference systems.
6. Store raw data without modification.
7. Record source metadata and retrieval time.
```

## 5.2 Recommended tools

```text
Python
Requests / HTTP clients
Pandas
Xarray
GeoPandas
Rasterio
Shapely
Dask (when data volume requires it)
```

## 5.3 Raw data principle

Keep raw data separately from processed data:

```text
/raw
/processed
/features
/models
/predictions
```

Never overwrite raw source data.

---

# 6. Data Harmonization

Different data sources will have different:

```text
- coordinate systems
- spatial resolutions
- temporal resolutions
- missing-value conventions
- units
- timestamps
```

The harmonization layer converts them to a common analytical representation.

## 6.1 Standard spatial reference

Use a consistent CRS for spatial calculations.

Important rule:

> Reproject into an appropriate projected CRS before calculating areas/distances.

## 6.2 Standard time reference

Store timestamps in UTC internally where possible, while preserving local-time information for Indian forecasts and daily health analysis.

Fields:

```text
timestamp_utc
timestamp_local
date_local
hour_local
```

---

# 7. Ward Boundary Layer

Ward polygons are the central spatial reference for the final system.

Required fields:

```text
ward_id
city
zone
geometry
area_m2
```

Every spatial feature ultimately needs to be mapped to a `ward_id`.

---

# 8. Spatial Feature Extraction Engine

This is the component that converts raw raster/vector data into ward-level features.

## 8.1 Raster -> Ward

For raster layers such as NDVI or LST:

```text
Raster pixels
     |
     v
Ward polygon mask
     |
     v
Zonal statistics
     |
     v
Ward features
```

Recommended statistics:

```text
mean
median
minimum
maximum
standard_deviation
percentile_10
percentile_90
pixel_count
area_above_threshold
```

Use:

```text
Rasterio
GeoPandas
NumPy
zonal-statistics tooling
```

## 8.2 Vector -> Ward

For OSM polygons/lines/points:

```text
OSM feature
     |
     v
Spatial intersection with ward
     |
     v
Area / length / count aggregation
     |
     v
Ward feature table
```

Examples:

```text
construction_area_m2
construction_site_count
road_length_km
building_area_m2
building_count
hospital_count
water_area_m2
```

---

# 9. Vegetation Feature Pipeline

## 9.1 NDVI

Calculate:

```text
NDVI = (NIR - RED) / (NIR + RED)
```

For Sentinel-2, a standard implementation can use:

```text
B08 = NIR
B04 = Red
```

## 9.2 Ward aggregation

For every ward:

```text
ndvi_mean
ndvi_median
ndvi_p90
vegetation_area_m2
vegetation_percentage
high_vegetation_percentage
```

## 9.3 Tree/green-space features

Where the available land-cover product supports them:

```text
tree_cover_percentage
grass_cover_percentage
vegetation_fraction
```

---

# 10. Land Surface Temperature Pipeline

Land Surface Temperature should be treated separately from air temperature.

```text
Satellite LST
      |
      v
Cloud / quality filtering
      |
      v
Spatial resampling if required
      |
      v
Ward zonal statistics
      |
      v
LST features
```

Ward features:

```text
lst_mean
lst_max
lst_p90
lst_std
```

Temporal features:

```text
lst_daily
lst_anomaly
lst_rolling_mean
```

LST should be aligned with cloud/quality flags where available.

---

# 11. Built Environment Pipeline

Derive:

```text
building_count
building_area_m2
building_density
built_up_percentage
road_length_km
road_density
impervious_surface_proxy
```

These features help the model distinguish wards with different urban forms even when forecast air temperature is similar.

---

# 12. Construction Exposure Pipeline

Use spatial construction features rather than a manually assigned construction flag.

```text
OSM / authoritative GIS construction features
                    |
                    v
           Ward spatial intersection
                    |
                    v
        +--------------------------+
        | construction_site_count  |
        | construction_area_m2     |
        | construction_density     |
        +--------------------------+
                    |
                    v
       Combine with outdoor-worker data
                    |
                    v
        construction_exposure_index
```

A prototype exposure measure can be defined as a normalized combination of:

```text
construction_density
x
outdoor_worker_density
```

The index must be explicitly documented as a derived proxy unless validated against observed worker exposure.

---

# 13. Slum / High-Vulnerability Area Pipeline

Preferred approach:

```text
Official demographic / slum boundary information
                    |
                    v
               GIS matching
                    |
                    v
              Ward aggregation
```

Possible ward features:

```text
slum_population
slum_household_count
slum_percentage
slum_area_percentage
```

Where current fine-grained official boundaries do not exist, satellite-based classification should be treated as an advanced feature and validated before use as ground truth.

Do not silently infer or label informal settlements from imagery as factual without validation.

---

# 14. Weather -> Ward Conversion

Weather sources may have station or grid resolution different from ward resolution.

## 14.1 Station data

Possible methods:

```text
Nearest station
Inverse Distance Weighting
Kriging (advanced)
```

## 14.2 Gridded forecast data

Preferred methods:

```text
Bilinear interpolation
Area-weighted aggregation
Grid-cell / polygon intersection
```

Output:

```text
ward_id

timestamp

temperature
relative_humidity
wind_speed
solar_radiation
...
```

### Important

Do not simply assign one city-level temperature to every ward if the objective is hyper-local modeling.

---

# 15. Thermal Stress Engine

The thermal engine is deterministic/scientific rather than ML-based.

Input:

```text
air_temperature
relative_humidity
wind_speed
solar_radiation
```

Possible additional inputs depend on the selected formulation.

Output:

```text
WBGT
UTCI
Heat Index
```

Also produce categorical states:

```text
normal
caution
high
severe
extreme
```

Thresholds must be documented with their authoritative source/formulation and not invented without justification.

---

# 16. Thermal Time-Series Features

For each ward and timestamp, derive:

```text
temperature_lag_1h
temperature_lag_6h
temperature_lag_12h
temperature_lag_24h

wbgt_lag_1h
wbgt_lag_24h
utci_lag_24h

rolling_temperature_24h
rolling_temperature_3d
rolling_temperature_7d

rolling_wbgt_3d
rolling_wbgt_7d
```

Heatwave persistence:

```text
consecutive_hot_days
consecutive_high_wbgt_days
consecutive_extreme_heat_days
```

Anomaly features:

```text
temperature_anomaly
wbgt_anomaly
utci_anomaly
lst_anomaly
humidity_anomaly
```

Baseline anomalies should be calculated relative to an explicitly defined historical climatology period.

---

# 17. Vulnerability Feature Layer

Ward-level vulnerability vector:

```text
population_density
elderly_percentage
children_percentage
outdoor_worker_density
slum_percentage
construction_density
building_density
vegetation_percentage
tree_cover_percentage
water_percentage
healthcare_accessibility
```

Not all features need to enter the ML model. Keep a clear distinction between:

```text
raw feature
engineered feature
composite index
model feature
```

---

# 18. Health Target Construction

## 18.1 Mortality

Preferred target:

```text
daily_death_count
```

Possible derived target:

```text
excess_mortality
```

where the baseline mortality expectation is estimated from historical non-heat periods or an appropriate statistical baseline.

## 18.2 Hospitalization

Possible targets:

```text
daily_admissions
daily_emergency_visits
heat_stroke_cases
heat-related admission count
```

## 18.3 Multiple targets

The system can support:

```text
Model A -> mortality risk
Model B -> hospitalization risk
```

or a multi-task architecture:

```text
shared representation
        |
   +----+----+
   |         |
 mortality   hospitalization
```

Start with separate models unless enough high-quality labeled data exist to justify multi-task learning.

---

# 19. Feature Table

The unified modeling table should conceptually become:

```text
ward_id
timestamp

# Weather
 temperature
 relative_humidity
 wind_speed
 solar_radiation
 dew_point
 pressure
 precipitation

# Thermal
 wbgt
 utci
 heat_index

# Temporal / heat persistence
 temperature_lag_24h
 wbgt_lag_24h
 rolling_temperature_3d
 rolling_wbgt_3d
 consecutive_hot_days
 temperature_anomaly
 wbgt_anomaly

# Environment
 ndvi_mean
 vegetation_percentage
 tree_cover_percentage
 lst_mean
 lst_anomaly
 built_up_percentage
 building_density
 road_density
 water_percentage
 construction_density

# Vulnerability
 population_density
 elderly_percentage
 children_percentage
 outdoor_worker_density
 slum_percentage
 healthcare_accessibility

# Health history
 mortality_lag_1d
 mortality_lag_3d
 mortality_rolling_7d
 hospitalization_lag_1d
 hospitalization_rolling_7d

# Target
 death_count_future
 hospitalization_count_future
```

The actual columns should depend on the resolution and availability of the underlying data.

---

# 20. Forecasting Architecture

The model must be able to answer:

> Given everything known at time T, what is the health risk at T+1 through T+5?

```text
Historical observations
        |
        v
Temporal feature sequence
        |
        +------------------------+
        |                        |
        v                        v
Past weather/health         Future weather forecasts
        |                        |
        +-----------+------------+
                    |
                    v
              Forecast model
                    |
            +-------+-------+
            |               |
            v               v
      mortality risk   hospitalization risk
        D+1 ... D+5      D+1 ... D+5
```

Future weather forecast variables should be treated as **known future covariates**, not as observed historical measurements.

---

# 21. Machine Learning Strategy

## 21.1 Baseline model

Use a tree-based baseline such as:

```text
LightGBM / XGBoost
```

Purpose:

```text
- establish a strong baseline
- inspect feature importance
- provide explainability
- test whether deep learning adds value
```

## 21.2 Main temporal model

Preferred advanced approach:

```text
Temporal Fusion Transformer (TFT)
```

The TFT is suited to:

```text
- multivariate time series
- static ward features
- historical covariates
- known future covariates
- multi-horizon prediction
```

Candidate alternatives:

```text
LSTM / GRU
Temporal Convolutional Networks
Transformer-based time-series models
```

The final choice must be based on validation performance and data volume rather than model novelty alone.

---

# 22. Spatial Modeling Strategy

There are two practical levels.

## Level 1 — Ward feature model

Treat each ward as a spatial unit and include environmental/demographic features:

```text
ward static features
+
weather time series
+
health time series
```

This is the recommended first implementation.

## Level 2 — Explicit spatial deep learning

If enough dense spatial-temporal data exist:

```text
Graph Neural Network
        or
Spatio-Temporal Graph Neural Network
```

Construct:

```text
Ward = node
Neighbouring wards = edges

Node features:
weather + thermal + demographics + environment

Target:
mortality / hospitalization
```

Only use this after establishing a reliable ward-level baseline.

---

# 23. Spatial Graph Construction

If a graph model is introduced:

```text
Ward A ----- Ward B
  |            |
  |            |
Ward C ----- Ward D
```

Edges can be defined using:

```text
shared boundary
centroid distance
k-nearest neighbours
```

Avoid arbitrary graph connections. Document the chosen construction rule.

---

# 24. Model Outputs

Every prediction should include more than a single class.

Example:

```json
{
  "ward_id": "W17",
  "prediction_date": "YYYY-MM-DD",
  "horizon_days": 3,
  "thermal_stress": {
    "wbgt": 35.8,
    "utci": 46.2,
    "heat_index": 49.1
  },
  "health_risk": {
    "mortality_risk": 0.87,
    "hospitalization_risk": 0.74
  },
  "risk_category": "VERY_HIGH",
  "prediction_interval": {
    "lower": 0.71,
    "upper": 0.93
  }
}
```

Values above are illustrative only.

---

# 25. Uncertainty and Calibration

For a public-health warning system, uncertainty must be visible.

Possible approaches:

```text
Quantile regression
Prediction intervals
Monte Carlo dropout
Deep ensembles
Conformal prediction
Bootstrap uncertainty
```

Also perform probability calibration:

```text
Platt scaling
Isotonic regression
```

Evaluate calibration using metrics such as:

```text
Brier score
Calibration curve
Expected Calibration Error
```

Do not present model probabilities as literal medical certainty.

---

# 26. Explainability Layer

Use:

```text
SHAP
Permutation importance
Attention / temporal attribution where appropriate
```

Example explanation:

```text
Ward W17 — high predicted health risk

Major contributing signals:
+ high WBGT
+ elevated nighttime temperature
+ high elderly density
+ high outdoor-worker density
+ high built-up percentage
+ low vegetation coverage
```

The explanation should identify **model features**, not claim causality unless causality has actually been established.

---

# 27. Risk Fusion / Decision Engine

Separate the raw model prediction from the final alert category.

```text
Thermal hazard
      +
Health risk
      +
Population vulnerability
      +
Uncertainty / confidence
      |
      v
Risk decision engine
      |
      v
Alert category
```

Possible levels:

```text
NORMAL
WATCH
HIGH
SEVERE
EXTREME
```

Thresholds must be configurable and documented.

---

# 28. Intervention Mapping

The decision engine can map risk states to recommended actions.

Example:

```text
EXTREME + high outdoor-worker exposure
    -> recommend outdoor-work hour adjustment

EXTREME + high elderly density
    -> recommend targeted vulnerable-population warning

EXTREME + high population + limited healthcare access
    -> recommend enhanced emergency preparedness

EXTREME + high exposure + available cooling infrastructure
    -> recommend cooling-centre activation
```

The system should distinguish between:

```text
MODEL PREDICTION
        and
RECOMMENDED ACTION
```

Actions should be configurable by the responsible authority rather than embedded as irreversible model behavior.

---

# 29. Alert Trigger Logic

Example conceptual rule:

```text
IF
    forecast thermal stress >= configured threshold
AND
    predicted health risk >= configured threshold
AND
    uncertainty is within acceptable bounds
THEN
    raise ward-level alert
```

This can be expanded with persistence:

```text
IF extreme risk persists for >= N forecast periods
THEN high-priority alert
```

Avoid a single noisy measurement causing repeated alerts.

---

# 30. Data Quality Checks

Before feature generation:

```text
Temperature range check
Humidity range check
Wind-speed range check
Radiation range check
Coordinate validity check
Timestamp validity check
Duplicate detection
Missing-value rate
Outlier detection
```

Examples:

```text
0 <= relative_humidity <= 100
solar_radiation >= 0
```

Physical constraints should be applied carefully according to the data source.

---

# 31. Missing Data Strategy

Different variables require different methods.

```text
Short weather gaps
    -> interpolation / forecast-aware imputation

Long weather gaps
    -> source replacement or missing indicator

Satellite cloud-covered pixels
    -> quality masking; temporal gap handling

Missing demographic data
    -> preserve missingness and use source-appropriate imputation

Missing health records
    -> do not automatically convert to zero deaths
```

A missing observation is not necessarily a zero observation.

---

# 32. Data Leakage Prevention

This is critical for the health forecasting model.

Never use:

```text
future mortality
future observed weather
future satellite observations
future labels
```

when pretending to make a real-time D+1 to D+5 forecast.

For future weather, use only the forecast that would have been available at prediction time.

---

# 33. Validation Strategy

Do **not** use a random train/test split for the main forecasting evaluation.

Use chronological splitting:

```text
TRAIN                    VALIDATION                TEST
|----------------------|------------------------|------------------|
older dates             later dates               latest dates
```

Preferred:

```text
rolling-origin evaluation
walk-forward validation
```

The test set must represent a genuinely future period.

---

# 34. Evaluation Metrics

## Mortality / count forecasting

```text
MAE
RMSE
Poisson deviance
Negative-binomial deviance where appropriate
```

## Risk classification

```text
Precision
Recall
F1
ROC-AUC
PR-AUC
```

For rare severe events, **PR-AUC and recall** can be more informative than accuracy.

## Probabilistic forecasts

```text
Brier score
CRPS (where applicable)
Calibration error
Prediction interval coverage
```

## Operational evaluation

```text
False alarm rate
Missed-event rate
Average warning lead time
```

---

# 35. Recommended Python Project Structure

```text
heatwave-system/
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── external/
│
├── ingestion/
│   ├── weather/
│   ├── satellite/
│   ├── osm/
│   ├── census/
│   └── health/
│
├── geospatial/
│   ├── ward_boundaries.py
│   ├── raster_features.py
│   ├── vector_features.py
│   ├── zonal_stats.py
│   └── spatial_join.py
│
├── thermal/
│   ├── wbgt.py
│   ├── utci.py
│   └── heat_index.py
│
├── features/
│   ├── weather_features.py
│   ├── temporal_features.py
│   ├── vulnerability_features.py
│   └── health_features.py
│
├── models/
│   ├── baseline/
│   ├── tft/
│   ├── spatial/
│   └── calibration/
│
├── training/
│   ├── dataset.py
│   ├── train.py
│   ├── validate.py
│   └── evaluate.py
│
├── inference/
│   ├── preprocess.py
│   ├── predict.py
│   └── uncertainty.py
│
├── explainability/
│   └── shap_analysis.py
│
├── risk_engine/
│   ├── scoring.py
│   ├── thresholds.py
│   └── interventions.py
│
├── schemas/
│   └── feature_schema.py
│
└── configs/
    ├── data_sources.yaml
    ├── feature_config.yaml
    └── model_config.yaml
```

---

# 36. Recommended Storage Model

A spatially enabled analytical database is preferred for processed ward-level data.

## PostgreSQL + PostGIS

Logical tables:

```text
wards
weather_observations
weather_forecasts
satellite_features
landcover_features
oosm_features
demographics
health_outcomes
thermal_indices
ward_features
predictions
alerts
```

For very large multidimensional weather/satellite data, object storage + Parquet/Zarr can be used alongside PostGIS.

Suggested analytical formats:

```text
Parquet -> tabular feature datasets
Zarr    -> multidimensional weather cubes
GeoParquet -> geospatial feature tables
```

---

# 37. Feature Generation Schedule

A practical pipeline can run in stages.

## Static / slow-changing features

Update periodically:

```text
ward boundaries
population
elderly density
outdoor-worker density
building density
vegetation baseline
road density
construction features
```

## Dynamic features

Update whenever new data arrive:

```text
weather observations
weather forecasts
LST
NDVI / vegetation state
WBGT
UTCI
heat index
health outcomes
```

## Real-time inference

```text
new weather forecast
      |
      v
ward weather transformation
      |
      v
thermal calculations
      |
      v
feature assembly
      |
      v
health model inference
      |
      v
risk decision
```

---

# 38. End-to-End Example

Suppose Ward W17 is being evaluated for a D+3 forecast.

```text
1. Forecast source provides:
   temperature, RH, wind, radiation

2. Weather grid is spatially mapped to W17.

3. Satellite/GIS feature store provides:
   NDVI, LST, vegetation, built-up area,
   construction density, water percentage.

4. Demographic layer provides:
   population density, elderly %, outdoor-worker %.

5. Thermal engine calculates:
   WBGT, UTCI, Heat Index.

6. Historical feature engine adds:
   recent heat persistence, anomalies,
   previous mortality and hospitalization signals.

7. Forecast model predicts:
   mortality/hospitalization risk for D+1 ... D+5.

8. Uncertainty layer calculates:
   prediction interval / calibrated probability.

9. Risk engine converts prediction into:
   NORMAL / WATCH / HIGH / SEVERE / EXTREME.

10. Intervention engine generates:
    recommended action categories.
```

---

# 39. Minimal Viable AI Pipeline for SIH

If implementation time is limited, build this first:

```text
Weather forecast
      |
      v
Ward-level weather aggregation
      |
      v
WBGT + UTCI + Heat Index
      |
      +----------------------+
      |                      |
      v                      v
Satellite/GIS            Demographics
NDVI                     elderly
LST                      outdoor workers
built-up                 population density
construction
      |                      |
      +----------+-----------+
                 |
                 v
          Feature table
                 |
                 v
        LightGBM baseline
                 |
                 v
        3–5 day health risk
                 |
                 v
        Ward-level risk map
```

Then upgrade the model to TFT and/or a spatial-temporal graph model only after the baseline works.

---

# 40. Advanced Version

The full research-oriented architecture is:

```text
              WEATHER FORECAST CUBES
                       |
              SATELLITE TIME SERIES
                       |
                  OSM / GIS
                       |
              DEMOGRAPHIC DATA
                       |
                  HEALTH DATA
                       |
                       v
              SPATIAL FEATURE ENGINE
                       |
           +-----------+-----------+
           |                       |
           v                       v
    STATIC WARD FEATURES    DYNAMIC TIME SERIES
           |                       |
           +-----------+-----------+
                       |
                       v
              THERMAL STRESS ENGINE
                 /      |       \
              WBGT     UTCI      HI
                 \      |       /
                       v
             SPATIO-TEMPORAL DATASET
                       |
              +--------+--------+
              |                 |
              v                 v
             TFT            ST-GNN
              |                 |
              +--------+--------+
                       |
                       v
              ENSEMBLE / CALIBRATION
                       |
                       v
                 RISK ENGINE
                       |
             +---------+---------+
             |                   |
             v                   v
        HEALTH RISK       INTERVENTION RISK
             |                   |
             +---------+---------+
                       |
                       v
                 WARD ALERTS
```

---

# 41. Technology Stack — Data/AI/Geospatial Only

| Layer | Recommended technology |
|---|---|
| Main language | Python |
| Numerical computing | NumPy, SciPy |
| Tabular processing | Pandas |
| Weather data cubes | Xarray, Dask |
| Raster processing | Rasterio |
| Vector GIS | GeoPandas, Shapely |
| Earth observation | Sentinel-2 / Landsat / Copernicus products |
| Geospatial storage | PostgreSQL + PostGIS |
| Analytical storage | Parquet / GeoParquet / Zarr |
| Thermal calculations | Python scientific implementations of WBGT, UTCI, Heat Index |
| ML baseline | LightGBM / XGBoost |
| Deep temporal model | PyTorch + Temporal Fusion Transformer implementation |
| Advanced spatial model | PyTorch Geometric / compatible spatio-temporal GNN tooling |
| Explainability | SHAP |
| Experiment tracking | MLflow (optional) |
| Data versioning | DVC (optional) |
| Parallel processing | Dask |

---

# 42. Recommended Implementation Order

```text
PHASE 1
Ward boundaries + weather ingestion

PHASE 2
Weather -> ward aggregation

PHASE 3
WBGT / UTCI / Heat Index engine

PHASE 4
Sentinel-2 -> NDVI / vegetation features

PHASE 5
LST + built-up + water features

PHASE 6
OSM -> construction / roads / buildings

PHASE 7
Demographic + vulnerability feature integration

PHASE 8
Historical health target integration

PHASE 9
Feature engineering + leakage-safe dataset

PHASE 10
LightGBM/XGBoost baseline

PHASE 11
TFT multi-horizon model

PHASE 12
Uncertainty + calibration

PHASE 13
Explainability

PHASE 14
Risk/decision engine

PHASE 15
Optional spatial-temporal GNN
```

---

# 43. Critical Data Feasibility Rule

The architecture must preserve the true resolution of every source.

```text
If health data = district/day:
    train/evaluate health model at district/day.

If health data = city/day:
    train/evaluate health model at city/day.

If health data = ward/day:
    ward-level mortality modeling becomes possible.
```

Environmental features can still be calculated at ward resolution even when health labels are coarser, but the resulting ward-level output must be described correctly as a **vulnerability/exposure-adjusted spatial risk product**, not falsely represented as a directly observed ward-level mortality model.

---

# 44. Final Core Principle

The system should learn from **observed spatial and temporal conditions**, not manually assigned ward scores.

```text
SATELLITE
   -> greenery / LST / land cover

GIS / OSM
   -> construction / roads / buildings / water / infrastructure

CENSUS / DEMOGRAPHICS
   -> elderly / outdoor workers / population / vulnerability

WEATHER
   -> temperature / RH / wind / radiation

HEALTH
   -> mortality / hospitalizations

             ALL ALIGNED BY
          TIME + SPACE + WARD
                    |
                    v
           THERMAL STRESS ENGINE
                    |
                    v
            HEALTH ML MODEL
                    |
                    v
          UNCERTAINTY + EXPLANATION
                    |
                    v
             WARD-LEVEL RISK
                    |
                    v
              ALERT DECISION
```
