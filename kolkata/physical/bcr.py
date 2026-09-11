import geopandas as gpd
import osmnx as ox

def get_building_coverage_ratio(ward_polygon_4326, ward_utm_geom) -> dict:
    """Computes Building Coverage Ratio (BCR) = Footprint Area / Ward Area."""
    total_area_sqm = ward_utm_geom.area
    try:
        buildings = ox.features_from_polygon(ward_polygon_4326, tags={"building": True})
        buildings_utm = buildings.to_crs(epsg=32645)
        built_area_sqm = float(buildings_utm.geometry.area.sum())
        building_count = len(buildings)
        bcr = min(built_area_sqm / total_area_sqm, 1.0)
    except Exception as e:
        print(f"    [BCR WARNING] OSM building query failed: {e}")
        built_area_sqm, building_count, bcr = 0.0, 0, 0.0

    return {
        "building_count": building_count,
        "built_area_sqm": round(built_area_sqm, 2),
        "bcr": round(bcr, 4)
    }