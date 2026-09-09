import pandas as pd

def get_household_crowding(ward_row: pd.Series) -> dict:
    """Calculates average occupants per household (nocturnal heat retention & metabolic load)."""
    pop = float(ward_row["TOT_P"])
    households = float(ward_row["No_HH"])
    crowding = pop / max(households, 1.0)
    return {
        "total_households": int(households),
        "household_crowding": round(crowding, 2)
    }