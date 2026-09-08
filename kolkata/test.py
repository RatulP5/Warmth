import sys
import geopandas as gpd
import pandas as pd

print("Testing Census read...", flush=True)
pca = pd.read_excel("data/DDW_PCA1916_2011_MDDS with UI.xlsx", sheet_name=0)
print(f"Census rows loaded: {len(pca)}", flush=True)

print("Testing GeoJSON read...", flush=True)
gdf = gpd.read_file("data/kmc_wards.geojson")
print(f"GeoJSON wards loaded: {len(gdf)}", flush=True)

print("Basic tests passed. Any stall after this is an external API call (OSM or Planetary Computer).", flush=True)