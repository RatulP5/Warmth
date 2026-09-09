import pandas as pd

def get_marginality_index(ward_row: pd.Series) -> dict:
    """Calculates illiteracy and SC/ST shares (proxies for lower adaptive cooling capacity)."""
    pop = float(ward_row["TOT_P"])
    illiterate = float(ward_row["P_ILL"])
    sc_st = float(ward_row["P_SC"] + ward_row["P_ST"])
    
    illit_ratio = illiterate / pop if pop > 0 else 0.0
    sc_st_ratio = sc_st / pop if pop > 0 else 0.0
    return {
        "illiteracy_pct": round(illit_ratio * 100, 2),
        "sc_st_pct": round(sc_st_ratio * 100, 2),
        "marginality_proxy": round((illit_ratio + sc_st_ratio) / 2.0, 4)
    }