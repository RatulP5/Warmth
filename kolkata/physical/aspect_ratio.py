import pandas as pd
import osmnx as ox

def get_canyon_aspect_ratio(ward_polygon_4326) -> dict:
    """Computes average Street Canyon Aspect Ratio (H/W)."""
    # 1. Height estimation
    try:
        buildings = ox.features_from_polygon(ward_polygon_4326, tags={"building": True})
        if "height" in buildings.columns:
            h = pd.to_numeric(buildings["height"].str.extract(r"(\d+[\.\d+]*)")[0], errors="coerce")
        elif "building:levels" in buildings.columns:
            h = pd.to_numeric(buildings["building:levels"], errors="coerce") * 3.2
        else:
            h = pd.Series([8.0] * len(buildings))
        avg_height = float(h.fillna(8.0).mean())
    except Exception as e:
        print(f"    [ASPECT WARNING] OSM building height query failed: {e}")
        avg_height = 8.0

    # 2. Width estimation
    try:
        roads = ox.features_from_polygon(ward_polygon_4326, tags={"highway": True})
        if "width" in roads.columns:
            w = pd.to_numeric(roads["width"].str.extract(r"(\d+[\.\d+]*)")[0], errors="coerce")
        elif "lanes" in roads.columns:
            w = pd.to_numeric(roads["lanes"], errors="coerce") * 3.0
        else:
            w = pd.Series([6.0] * len(roads))
        avg_width = float(w.fillna(6.0).mean())
    except Exception as e:
        print(f"    [ASPECT WARNING] OSM road width query failed: {e}")
        avg_width = 6.0

    hw_ratio = round(avg_height / max(avg_width, 1.0), 3)
    return {
        "avg_building_height_m": round(avg_height, 2),
        "avg_street_width_m": round(avg_width, 2),
        "aspect_ratio_hw": hw_ratio
    }