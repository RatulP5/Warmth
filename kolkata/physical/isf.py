import geopandas as gpd
import osmnx as ox

def get_impervious_surface_fraction(ward_polygon_4326, ward_utm_geom, built_area_sqm: float) -> dict:
    """Computes Impervious Surface Fraction (ISF) = (Building Area + Road Area) / Ward Area."""
    total_area_sqm = ward_utm_geom.area
    try:
        roads = ox.features_from_polygon(ward_polygon_4326, tags={"highway": True})
        roads_utm = roads.to_crs(epsg=32645)
        
        # Estimate width: tag -> lanes*3.0 -> default 6.0m for inner lanes
        if "width" in roads.columns:
            widths = roads["width"].str.extract(r"(\d+[\.\d+]*)")[0].astype(float)
        elif "lanes" in roads.columns:
            widths = roads["lanes"].astype(float) * 3.0
        else:
            widths = None
            
        road_widths = widths.fillna(6.0) if widths is not None else 6.0
        road_area_sqm = float((roads_utm.geometry.length * road_widths).sum())
        total_paved_sqm = min(built_area_sqm + road_area_sqm, total_area_sqm)
        isf = min(total_paved_sqm / total_area_sqm, 1.0)
    except Exception as e:
        print(f"    [ISF WARNING] OSM road query failed: {e}")
        road_area_sqm, isf = 0.0, min(built_area_sqm / total_area_sqm, 1.0)

    return {
        "road_area_sqm": round(road_area_sqm, 2),
        "isf": round(isf, 4)
    }