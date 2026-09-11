"""
heatwave_ml/exposure
────────────────────
Step 4 of the urban extreme-heat pipeline.
Synthesizes daily thermal hazard indices, environmental context, and
official Census demographics & outdoor exposure proxies.
"""

def __getattr__(name):
    if name == "ExposurePipeline":
        from exposure.pipeline import ExposurePipeline
        globals()["ExposurePipeline"] = ExposurePipeline
        return globals()[name]
    if name == "CensusExposureLoader":
        from exposure.census import CensusExposureLoader
        globals()["CensusExposureLoader"] = CensusExposureLoader
        return globals()[name]
    if name == "ThermalExposureAggregator":
        from exposure.thermal_exposure import ThermalExposureAggregator
        globals()["ThermalExposureAggregator"] = ThermalExposureAggregator
        return globals()[name]
    raise AttributeError(f"module 'exposure' has no attribute {name!r}")

__all__ = [
    "ExposurePipeline",
    "CensusExposureLoader",
    "ThermalExposureAggregator",
]
