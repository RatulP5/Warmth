"""Print basic metadata for GeoJSON files in the project root."""

from pathlib import Path

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    files = sorted(PROJECT_ROOT.glob("*.geojson"))
    if not files:
        print("No GeoJSON files found in the project root.")
        return

    for path in files:
        layer = gpd.read_file(path)
        print(f"{path.name}: {len(layer):,} rows, CRS={layer.crs}")
        print(f"  columns: {', '.join(layer.columns)}")
        print(f"  geometry: {layer.geometry.geom_type.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
