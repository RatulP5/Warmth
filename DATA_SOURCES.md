# External Data Sources and Provenance Specification

This document details all external observation, numerical forecast, satellite raster, and vector sources integrated into the Extreme Heatwave Early Warning system.

---

## 1. Meteorological Forecasts & Climatological Archive

### **Open-Meteo Weather API**
- **Provider**: Open-Meteo GmbH (collaborating with DWD, NOAA, ECMWF)
- **URL**: [https://open-meteo.com/](https://open-meteo.com/)
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Spatial Resolution**: ~1.5 km to 11 km depending on underlying numerical model (ECMWF IFS / GFS)
- **Temporal Resolution**: Hourly
- **Variables Ingested**:
  - `temperature_2m` (°C) — Ambient dry-bulb air temperature
  - `relative_humidity_2m` (%) — Moisture saturation percentage
  - `wind_speed_10m` (km/h converted to m/s) — Convective cooling flux
  - `direct_normal_irradiance` (W/m²) — Downward solar radiant flux
  - `surface_pressure` (hPa) — Atmospheric pressure
  - `precipitation` (mm) — Rainfall accumulation
- **Limitations**:
  - Interpolated gridded models can underestimate microscale urban canyon heat retention without local boundary layer adjustments.
  - Requires fallback regional centroids when network rate limits occur.

---

## 2. Satellite Surface Observations

### **Copernicus Sentinel-2 (MSI)**
- **Provider**: European Space Agency (ESA) / Copernicus Programme
- **URL**: [https://sentinels.copernicus.eu/](https://sentinels.copernicus.eu/)
- **License**: Open Access / Full, Free, and Open License
- **Spatial Resolution**: 10 meters (Bands B04, B08)
- **Temporal Resolution**: 5-day revisit time
- **Variables Ingested**:
  - Band 4 (Red, 665 nm)
  - Band 8 (Near-Infrared - NIR, 842 nm)
- **Derived Products**:
  - Normalized Difference Vegetation Index (NDVI): $(NIR - Red) / (NIR + Red)$
  - Zonal mean, median, standard deviation, p10, p90, and percentage of high vegetation (NDVI >= 0.40).
- **Limitations**:
  - Optical imagery is obstructed by monsoon cloud cover; requires cloud masking and temporal composite interpolation.

### **Landsat 8/9 (TIRS Band 10)**
- **Provider**: United States Geological Survey (USGS) / NASA
- **URL**: [https://landsat.gsfc.nasa.gov/](https://landsat.gsfc.nasa.gov/)
- **License**: Public Domain
- **Spatial Resolution**: 100 meters resampled to 30 meters
- **Temporal Resolution**: 16-day revisit time (8-day combined with Landsat 8 & 9)
- **Variables Ingested**:
  - Band 10 (Thermal Infrared - TIRS 1, 10.60–11.19 µm)
- **Derived Products**:
  - Land Surface Temperature (LST, °C)
  - Ward-level thermal anomalies relative to regional baseline.
- **Limitations**:
  - Represents radiometric skin temperature rather than ambient air temperature ($T_a$); strictly maintained as a separate feature in the pipeline.

### **ESA WorldCover 10m**
- **Provider**: European Space Agency (ESA)
- **URL**: [https://esa-worldcover.org/](https://esa-worldcover.org/)
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Spatial Resolution**: 10 meters
- **Derived Products**:
  - Ward surface percentages: Tree Cover, Grassland, Built-up area, Open Water, Bare Soil.
- **Limitations**:
  - Static annual classification; does not capture real-time seasonal foliage variation.

---

## 3. Geospatial Vector Morphology

### **OpenStreetMap (Overpass API)**
- **Provider**: OpenStreetMap Foundation & Overpass API Contributors
- **URL**: [https://overpass-api.de/](https://overpass-api.de/)
- **License**: Open Database License (ODbL)
- **Spatial Resolution**: Centimeter-to-meter coordinate vector polygons and nodes
- **Variables Ingested**:
  - Cooling Buffers: `leisure=park`, `natural=water`, `natural=tree`
  - High-Absorption Roofs: `roof:material~tin|metal|corrugated_iron`
  - Active Construction Sites: `landuse=construction`, `building=construction`
  - Total Building Density: `building`
  - Road Infrastructure: `highway`
- **Derived Products**:
  - Building density ($count / km^2$)
  - Road density ($km / km^2$)
  - Construction density ($sites / km^2$)
  - Construction Exposure Index (CEI) proxy
  - Morphological Heat Vulnerability Index (HVI)
- **Limitations**:
  - Tag completeness depends on local community mapping density; informal settlements may have underreported roof material tags.

---

## 4. Socio-Demographic & Health Registries

### **Census of India / Municipal Registrar**
- **Provider**: Office of the Registrar General & Census Commissioner, India / Kolkata Municipal Corporation
- **Spatial Granularity**: Ward / Sub-district
- **Variables Ingested**:
  - Total resident population & population density ($pop / km^2$)
  - Elderly population share (% >= 65 years)
  - Child population share (% <= 5 years)
  - Outdoor informal worker density (street vendors, daily wage laborers, construction)
  - Notified and non-notified slum settlement household shares (%)
- **Limitations**:
  - Decennial census updates require intercensal demographic projections; must never conflate district averages with ward-level records.

### **Civil Registration System (CRS) & Hospital Emergency Admissions**
- **Provider**: Department of Health & Family Welfare / State Disaster Management Authority
- **Spatial Granularity**: Ward-level (preferred) or City/District level with explicit metadata flag
- **Variables Ingested**:
  - All-cause daily mortality
  - Emergency room hospitalizations (heat-exhaustion, cardiovascular decompensation, acute renal failure)
- **Data Integrity Protocol**:
  - Missing records are explicitly preserved as `NaN` / missing indicators; **NEVER** filled with zeros.
