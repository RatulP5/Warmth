# Data Schema

## Canonical keys
```text
ward_id
city
zone
timestamp_utc
timestamp_local
date_local
```

## Ward geometry table
```text
ward_id: string
city: string
zone: string
area_m2: float
geometry: Polygon/MultiPolygon
```

## Weather table
```text
ward_id
timestamp
source
temperature_c
relative_humidity_pct
wind_speed_mps
solar_radiation_wm2
dew_point_c
pressure_hpa
precipitation_mm
cloud_cover_pct
```

## Thermal table
```text
ward_id
timestamp
wbgt_c
utci_c
heat_index_c
wbgt_category
utci_category
heat_index_category
```

## Environmental table
```text
ward_id
ndvi_mean
ndvi_median
ndvi_p10
ndvi_p90
vegetation_percentage
tree_cover_percentage
grass_cover_percentage
built_up_percentage
water_percentage
lst_mean_c
lst_p90_c
lst_anomaly_c
building_count
building_area_m2
building_density
road_length_km
road_density
construction_site_count
construction_area_m2
construction_density
```

## Vulnerability table
```text
ward_id
total_population
population_density
elderly_population
elderly_percentage
children_population
children_percentage
outdoor_worker_population
outdoor_worker_percentage
outdoor_worker_density
slum_population
slum_percentage
housing_density
electricity_access
water_access
healthcare_accessibility
```

## Temporal health features
```text
mortality_lag_1d
mortality_lag_3d
mortality_rolling_7d
hospitalization_lag_1d
hospitalization_rolling_7d
```

## Thermal temporal features
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
consecutive_hot_days
consecutive_high_wbgt_days
consecutive_extreme_heat_days
temperature_anomaly
wbgt_anomaly
utci_anomaly
humidity_anomaly
```

## Target schema
```text
future_date
mortality_count_future
hospitalization_count_future
```

## Prediction schema
```text
ward_id
prediction_timestamp
horizon_days
wbgt
utci
heat_index
mortality_prediction
hospitalization_prediction
mortality_probability
hospitalization_probability
lower_bound
upper_bound
risk_category
model_version
```

## Missingness
Use null/NaN plus explicit imputation flags where required. Never encode unknown as zero unless the source itself explicitly reports zero.

## Units
Use SI units internally where practical. Column names must make units clear when ambiguity exists.
