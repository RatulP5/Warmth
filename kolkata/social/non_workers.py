import pandas as pd

def get_non_worker_ratio(ward_row: pd.Series) -> dict:
    """Calculates proportion of non-workers remaining inside dwellings during peak hours."""
    pop = float(ward_row["TOT_P"])
    non_workers = float(ward_row["NON_WORK_P"])
    ratio = non_workers / pop if pop > 0 else 0.0
    return {
        "non_workers_count": int(non_workers),
        "non_worker_pct": round(ratio * 100, 2),
        "non_worker_ratio": round(ratio, 4)
    }