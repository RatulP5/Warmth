"""
Data points extracted from CEEW-IITG-IIM-A working paper (Dholakia et al., 2015).
"""

# Climate classification & representative city mapping
# Table S.1 (Page 30) & Table S.6 (Page 39)
CLIMATE_ZONE = "Warm & Humid"
REPRESENTATIVE_CITY = "Mumbai"  # Used as regional anchor for Kolkata

# Kolkata demographic baselines
# Table S.9 (Page 43, row 'Kolkata')
POPULATION_2011 = 14_112_536
ANNUAL_CRUDE_DEATH_RATE_PER_1K = 6.5

# Minimum Mortality Temperature (MMT)
# Table S.5 (Page 36, row 'Mumbai')
MMT_HOT_SEASON_TMAX = 30.9  # °C

# Empirical coordinates from Figure S.2 (Page 37, curve 'Mumbai')
EXPOSURE_ANCHORS = [
    {"t_max": 30.9, "rr": 1.000},  # Baseline
    {"t_max": 36.0, "rr": 1.030},  # ~3.0% excess risk
    {"t_max": 41.0, "rr": 1.147}   # ~14.7% excess risk
]

# Lag window size
MAX_LAG_DAYS = 3  # Lags 0, 1, 2, 3