import pandas as pd

def get_outdoor_labor_ratio(ward_row: pd.Series) -> dict:
    """Calculates Marginal Other Workers (proxy for outdoor daily-wage/construction labor)."""
    pop = float(ward_row["TOT_P"])
    labor = float(ward_row["MARG_OT_P"])
    ratio = labor / pop if pop > 0 else 0.0
    return {
        "outdoor_labor_count": int(labor),
        "outdoor_labor_pct": round(ratio * 100, 2),
        "outdoor_labor_ratio": round(ratio, 4)
    }