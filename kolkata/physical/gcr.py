import numpy as np
import geopandas as gpd
import pystac_client
import planetary_computer
import rioxarray

def get_green_coverage_ratio(ward_4326_gdf: gpd.GeoDataFrame) -> dict:
    """Calculates NDVI and Green Coverage Ratio (GCR, fraction of pixels NDVI > 0.25)."""
    bbox = list(ward_4326_gdf.total_bounds)
    try:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace
        )
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime="2025-01-01/2025-04-30",
            query={"eo:cloud_cover": {"lt": 10}},
            sortby=[{"field": "properties.eo:cloud_cover", "direction": "asc"}],
            max_items=1
        )
        items = list(search.items())
        if not items:
            return {"gcr": 0.0, "mean_ndvi": 0.0}

        item = items[0]
        geoms = list(ward_4326_gdf.geometry.values)
        crs = ward_4326_gdf.crs
        red = rioxarray.open_rasterio(item.assets["B04"].href).rio.clip(geoms, crs)
        nir = rioxarray.open_rasterio(item.assets["B08"].href).rio.clip(geoms, crs)

        red_f = red.astype("float32")
        nir_f = nir.astype("float32")
        ndvi = (nir_f - red_f) / (nir_f + red_f + 1e-8)
        
        valid = ndvi.values.flatten()
        valid = valid[~np.isnan(valid)]
        
        if len(valid) == 0:
            return {"gcr": 0.0, "mean_ndvi": 0.0}

        green_pixels = (valid > 0.25).sum()
        gcr = float(green_pixels / len(valid))
        mean_ndvi = float(np.mean(valid))
    except Exception as e:
        print(f"    [GCR WARNING] Satellite NDVI query failed: {e}")
        gcr, mean_ndvi = 0.0, 0.0

    return {
        "gcr": round(gcr, 4),
        "mean_ndvi": round(mean_ndvi, 4)
    }