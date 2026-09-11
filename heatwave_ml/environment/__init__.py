"""
heatwave_ml/environment
────────────────────────
Step 3 of the urban extreme-heat ML pipeline.

Produces a ward-level environmental feature table (LST, NDVI, land-cover
fractions, OSM built-up/road density) for all Kolkata KMC wards across
monthly windows.  Output is a Parquet file ready to be joined with
meteorological data from the forecasting module.

Usage
-----
  # Run full pipeline from heatwave_ml/ directory:
  python -m environment.pipeline

  # Single ward test:
  python -m environment.pipeline --ward KMC_Ward_65

  # In code:
  from environment import EnvironmentPipeline
  EnvironmentPipeline().run()
"""

# Lazy imports to avoid circular sys.modules warning when running as __main__
def __getattr__(name):
    if name in ("EnvironmentPipeline", "WardLoader"):
        from environment.pipeline import EnvironmentPipeline, WardLoader
        globals()["EnvironmentPipeline"] = EnvironmentPipeline
        globals()["WardLoader"] = WardLoader
        return globals()[name]
    if name in ("SatelliteExtractor", "OsmExtractor"):
        from environment.extractors import SatelliteExtractor, OsmExtractor
        globals()["SatelliteExtractor"] = SatelliteExtractor
        globals()["OsmExtractor"] = OsmExtractor
        return globals()[name]
    raise AttributeError(f"module 'environment' has no attribute {name!r}")

__all__ = ["EnvironmentPipeline", "WardLoader", "SatelliteExtractor", "OsmExtractor"]
