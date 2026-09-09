import pandas as pd

def get_children_ratio(ward_row: pd.Series) -> dict:
    """Calculates proportion of children aged 0-6 (high dehydration & thermal sensitivity)."""
    pop = float(ward_row["TOT_P"])
    children = float(ward_row["P_06"])
    ratio = children / pop if pop > 0 else 0.0
    return {
        "children_count": int(children),
        "children_pct": round(ratio * 100, 2),
        "children_ratio": round(ratio, 4)
    }