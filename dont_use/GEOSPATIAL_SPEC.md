# Geospatial Feature Engineering Specification

## Objective
Convert actual spatial datasets into ward-level features without manual ward-level hardcoding.

## CRS
- Store source CRS metadata.
- Use a geographic CRS for interoperability.
- Reproject to an appropriate projected CRS before area/length/distance calculations.
- Record the calculation CRS.

## Raster → ward
Used for NDVI, LST, land cover, and other gridded variables.

Pipeline:
```text
raster
 ↓
quality/cloud/nodata masking
 ↓
reproject/resample when required
 ↓
ward polygon mask
 ↓
zonal statistics
 ↓
ward feature table
```

Default statistics:
- mean
- median
- min/max
- standard deviation
- p10/p90
- valid pixel count
- area above/below configured threshold

## NDVI
For Sentinel-2:
```text
NDVI = (NIR - Red) / (NIR + Red)
NIR = B08
Red = B04
```
Mask invalid pixels and preserve the acquisition date.

## LST
Keep Land Surface Temperature separate from air temperature. Preserve quality flags and acquisition timestamps.

Ward features:
```text
lst_mean
lst_median
lst_max
lst_p90
lst_std
lst_anomaly
```

## Land cover
Where supported, aggregate classes into ward percentages:
```text
tree_cover
vegetation
grass
built_up
water
bare_soil
```
Percentages should sum sensibly after accounting for unknown/masked pixels.

## Vector → ward
For OSM or authoritative vector layers:
```text
vector features
 ↓
geometry validation
 ↓
spatial intersection with wards
 ↓
count / length / area aggregation
```

Examples:
- buildings → count and footprint area
- roads → length and density
- construction → count, area, density
- water → area and percentage
- hospitals → count

## Weather → ward
For station data:
- nearest station
- inverse-distance weighting
- optionally kriging as an advanced experiment

For gridded data:
- bilinear interpolation
- area-weighted aggregation
- cell/polygon intersection

The chosen method must be stored in metadata/configuration.

## Construction exposure
A prototype proxy may combine normalized construction density and normalized outdoor-worker density. Label it as an exposure proxy, not measured individual exposure.

## Slum / informal settlement mapping
Prefer official boundaries/statistics. Satellite-derived classification may be an experimental feature only and must not be presented as authoritative ground truth without validation.

## Spatial integrity tests
Test:
- invalid geometries
- CRS mismatches
- duplicate ward IDs
- missing ward geometry
- unexpected overlap
- impossible feature percentages
- area calculations
