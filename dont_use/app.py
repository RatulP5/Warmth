"""Extreme Heatwave Early Warning & Human Thermal Stress Index — Interactive Dashboard.

This Streamlit application acts as the operational municipal command center and
scientific inspection portal for the Python-only heatwave prediction pipeline.

Run command:
    streamlit run app.py
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st

# -----------------------------------------------------------------------------
# Configuration & Theming
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Heatwave Early Warning Platform",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS styling for emergency-ops aesthetics
st.markdown(
    """
    <style>
    .metric-card {
        background-color: rgba(255, 75, 75, 0.05);
        border: 1px solid rgba(255, 75, 75, 0.2);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .badge-extreme {
        background-color: #8B0000;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-severe {
        background-color: #D9534F;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-warning {
        background-color: #F0AD4E;
        color: black;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Data Ingestion Helpers
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Fallback path if run from project root
if not DATA_DIR.exists():
    DATA_DIR = Path("data")


@st.cache_data
def load_pipeline_data():
    """Loads all prediction, feature, and audit artifacts."""
    pred_pq = DATA_DIR / "predictions" / "ward_predictions.parquet"
    actions_pq = DATA_DIR / "predictions" / "recommended_actions.parquet"
    spatial_pq = DATA_DIR / "features" / "spatial_features.parquet"
    if not spatial_pq.exists():
        spatial_pq = DATA_DIR / "demo" / "spatial_features.parquet"

    geojson_path = DATA_DIR / "predictions" / "ward_predictions.geojson"
    if not geojson_path.exists():
        geojson_path = DATA_DIR / "demo" / "wards.geojson"

    report_path = DATA_DIR / "reports" / "data_quality_report.json"

    df_preds = pd.read_parquet(pred_pq) if pred_pq.exists() else pd.DataFrame()
    df_actions = pd.read_parquet(actions_pq) if actions_pq.exists() else pd.DataFrame()
    df_spatial = pd.read_parquet(spatial_pq) if spatial_pq.exists() else pd.DataFrame()

    geojson_data = None
    if geojson_path.exists():
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

    audit_report = None
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            audit_report = json.load(f)

    # Ward metadata lookup
    ward_names = {
        "KOL-DD": "Dum Dum (North)",
        "KOL-SL": "Salt Lake Sector V (IT/East)",
        "KOL-BB": "Burrabazar (Central Market)",
        "KOL-BH": "Behala South (High Density)",
        "KOL-GH": "Gariahat Urban (Commercial)",
    }

    if not df_preds.empty and "ward_name" not in df_preds.columns:
        df_preds["ward_name"] = df_preds["ward_id"].map(ward_names).fillna(df_preds["ward_id"])

    return df_preds, df_actions, df_spatial, geojson_data, audit_report


df_preds, df_actions, df_spatial, geojson_data, audit_report = load_pipeline_data()

# -----------------------------------------------------------------------------
# Sidebar Navigation & Filters
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/thermometer.png", width=64)
    st.title("Heatwave AI Portal")
    st.caption("Smart India Hackathon (MoES) — Thermal Stress & Early Warning")

    if not df_preds.empty:
        dates_available = sorted(df_preds["forecast_date"].unique().tolist())
        selected_date = st.selectbox("📅 Forecast Horizon Date", options=dates_available, index=0)

        wards_available = ["All Wards"] + sorted(df_preds["ward_id"].unique().tolist())
        selected_ward = st.selectbox("📍 Focus Administrative Ward", options=wards_available, index=0)
    else:
        selected_date = None
        selected_ward = "All Wards"

    st.markdown("---")
    st.markdown(
        """
        **System Parameters**:
        - **Horizon**: $D+1 \dots D+5$ (Multi-Horizon)
        - **Lookback**: 14 days
        - **Coverage**: Conformal 80% CI
        - **Primary Target**: Emergency Surge %
        - **Night Recovery Deficit**: $T_{\\min} \\ge 28^\\circ\\text{C}$
        """
    )
    st.markdown("---")
    st.caption("Built in strict alignment with `AGENTS.md`, `ML_SPEC.md` and `GEOSPATIAL_SPEC.md`.")

# -----------------------------------------------------------------------------
# Main Application Tabs
# -----------------------------------------------------------------------------
tabs = st.tabs([
    "🚨 Executive Dashboard",
    "🗺️ Ward Spatial Explorer",
    "📈 5-Day Health Surge",
    "🌡️ Biophysical Indices",
    "📋 Municipal Protocols",
    "🛡️ Model Card & Auditing"
])

if df_preds.empty:
    st.error("No prediction data found. Please run `python pipeline.py run-all --demo` first.")
    st.stop()

# Filter data by selected date
df_date = df_preds[df_preds["forecast_date"] == selected_date].copy()
if selected_ward != "All Wards":
    df_date = df_date[df_date["ward_id"] == selected_ward]

# -----------------------------------------------------------------------------
# Tab 1: Executive Dashboard
# -----------------------------------------------------------------------------
with tabs[0]:
    st.header(f"Executive Early Warning Briefing — {selected_date}")

    # Top KPI Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        peak_t = df_date["peak_temperature_c"].max()
        st.metric("Peak Dry-Bulb", f"{peak_t:.1f} °C", delta=f"{peak_t - 38:.1f} °C vs Climo", delta_color="inverse")
    with col2:
        peak_wbgt = df_date["peak_wbgt_c"].max()
        st.metric("Peak Outdoor WBGT", f"{peak_wbgt:.1f} °C", "Extreme Hazard" if peak_wbgt >= 32 else "High", delta_color="inverse")
    with col3:
        max_surge = df_date["surge_pct"].max()
        st.metric("Max Hospital Surge", f"+{max_surge:.1f}%", "Bed Demand Alert", delta_color="inverse")
    with col4:
        night_deficits = df_date["is_night_deficit"].sum()
        st.metric("Night Deficit Wards", f"{night_deficits} / {len(df_date)}", "T_min >= 28°C" if night_deficits > 0 else "Normal")
    with col5:
        extreme_count = (df_date["risk_tier"] == "EXTREME").sum()
        st.metric("EXTREME Risk Tier", f"{extreme_count} Wards", "Disaster Level", delta_color="inverse")

    # Critical Alert Callout if Night Deficit or Extreme
    if night_deficits > 0:
        st.error(
            f"⚠️ **CRITICAL NOCTURNAL DEFICIT ACTIVE**: {night_deficits} ward(s) sustain nighttime temperatures above 28°C. "
            "Cardiovascular core cooling failure imminent. Emergency open-park cooling shelters must be activated."
        )

    st.subheader("Ward Status Summary")
    display_cols = [
        "ward_id", "ward_name", "risk_tier", "peak_temperature_c",
        "min_night_temp_c", "peak_wbgt_c", "peak_heat_index_c", "surge_pct", "is_night_deficit"
    ]
    st.dataframe(
        df_date[display_cols].sort_values(by="surge_pct", ascending=False),
        use_container_width=True,
        column_config={
            "surge_pct": st.column_config.ProgressColumn(
                "Hospitalization Surge",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "is_night_deficit": st.column_config.CheckboxColumn("Night Deficit (≥28°C)"),
            "peak_wbgt_c": st.column_config.NumberColumn("Peak WBGT (°C)", format="%.1f"),
            "peak_temperature_c": st.column_config.NumberColumn("Peak Temp (°C)", format="%.1f"),
            "min_night_temp_c": st.column_config.NumberColumn("Night Min (°C)", format="%.1f"),
        }
    )

# -----------------------------------------------------------------------------
# Tab 2: Ward Spatial Explorer
# -----------------------------------------------------------------------------
with tabs[1]:
    st.header("Geospatial Ward Vulnerability & Urban Morphology")
    st.caption("Satellite zonal statistics derived from Sentinel-2 (NDVI), Landsat 8/9 (LST), and OpenStreetMap morphology.")

    col_map, col_attr = st.columns([3, 2])

    with col_map:
        st.subheader("Ward Geographic Risk Distribution")
        # Ward overview table with coordinates
        if not df_spatial.empty:
            merged_spatial = df_date.merge(df_spatial, on="ward_id", how="left")
            st.dataframe(
                merged_spatial[[
                    "ward_id", "ward_name", "risk_tier", "hvi_score", "tin_roofs_count",
                    "cooling_buffers_count", "population_density", "slum_percentage"
                ]],
                use_container_width=True
            )
        else:
            st.info("No spatial features parquet found.")

    with col_attr:
        st.subheader("Vulnerability Indicators")
        if not df_spatial.empty:
            st.write("**Morphological Heat Vulnerability Index (HVI)**:")
            st.latex(r"HVI = \frac{1.5 \cdot \text{tin\_roofs} + 2.0 \cdot \text{construction} + 0.05 \cdot \text{buildings}}{10 \cdot \max(1, \text{cooling\_buffers}) + 1}")
            st.bar_chart(df_spatial.set_index("ward_id")["hvi_score"])

# -----------------------------------------------------------------------------
# Tab 3: 5-Day Health Surge & Conformal Uncertainty
# -----------------------------------------------------------------------------
with tabs[2]:
    st.header("Multi-Horizon Hospital Bed Surge & Uncertainty")
    st.markdown(
        """
        Predictions generated using the **Temporal Fusion Multi-Horizon Engine** with **Split Conformal Prediction**.
        The shaded interval provides a **finite-sample coverage guarantee of 80%** ($1-\\alpha = 0.80$).
        """
    )

    chart_ward = selected_ward if selected_ward != "All Wards" else "KOL-DD"
    df_ward_forecast = df_preds[df_preds["ward_id"] == chart_ward].sort_values(by="forecast_date")

    st.subheader(f"Forecast Horizon for Ward: {chart_ward}")

    chart_data = df_ward_forecast[[
        "forecast_date", "surge_pct", "surge_interval_lower", "surge_interval_upper"
    ]].set_index("forecast_date")

    st.line_chart(chart_data)

    st.table(
        df_ward_forecast[[
            "forecast_date", "risk_tier", "surge_pct", "surge_interval_lower", "surge_interval_upper"
        ]].rename(columns={
            "surge_pct": "Point Prediction (%)",
            "surge_interval_lower": "Conformal Lower (80% CI)",
            "surge_interval_upper": "Conformal Upper (80% CI)",
        })
    )

# -----------------------------------------------------------------------------
# Tab 4: Biophysical Thermal Indices
# -----------------------------------------------------------------------------
with tabs[3]:
    st.header("Deterministic Biophysical Thermal Indices")
    st.caption("Calculated purely via physical formulations (Stull psychrometrics, ISO 7243 WBGT, NOAA Heat Index).")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Temperature vs. WBGT vs. UTCI")
        st.line_chart(
            df_preds[df_preds["ward_id"] == chart_ward].set_index("forecast_date")[[
                "peak_temperature_c", "peak_wbgt_c", "peak_utci_c", "peak_heat_index_c"
            ]]
        )

    with col_t2:
        st.subheader("Physical Formulations Applied")
        st.markdown(
            """
            **1. Stull (2011) Natural Wet-Bulb ($T_{\\text{nw}}$)**:
            Derived from dry-bulb air temperature ($T_a$) and relative humidity ($RH$) without ML approximation.

            **2. Black Globe Radiant Flux ($T_g$)**:
            $$T_g = T_a + \\frac{0.05 \\cdot S}{v_{10} + 0.5}$$
            accounting for direct solar radiation ($S$) and convective dissipation ($v_{10}$).

            **3. Outdoor Wet-Bulb Globe Temperature (ISO 7243)**:
            $$\\text{WBGT}_{\\text{outdoor}} = 0.7 T_{\\text{nw}} + 0.2 T_g + 0.1 T_a$$

            **4. Nocturnal Recovery Deficit ($T_{\\min} \\ge 28^\\circ\\text{C}$)**:
            Identifies nights where thermoregulatory cardiovascular recovery ceases.
            """
        )

# -----------------------------------------------------------------------------
# Tab 5: Municipal Protocols
# -----------------------------------------------------------------------------
with tabs[4]:
    st.header(f"Actionable Municipal Interventions — {selected_date}")
    st.caption("Triggered automatically by rule-based disaster management thresholds.")

    if not df_actions.empty:
        actions_filtered = df_actions[df_actions["forecast_date"] == selected_date]
        if selected_ward != "All Wards":
            actions_filtered = actions_filtered[actions_filtered["ward_id"] == selected_ward]

        if actions_filtered.empty:
            st.success("No emergency interventions triggered for this selection.")
        else:
            for _, act in actions_filtered.iterrows():
                tier_badge = (
                    f"<span class='badge-extreme'>{act['risk_tier']}</span>"
                    if act["risk_tier"] == "EXTREME"
                    else f"<span class='badge-severe'>{act['risk_tier']}</span>"
                )
                st.markdown(
                    f"""
                    <div class="metric-card">
                        {tier_badge} <strong>Ward {act['ward_id']}</strong>: {act['action']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.info("No recommended actions parquet file found.")

# -----------------------------------------------------------------------------
# Tab 6: Model Card & Auditing
# -----------------------------------------------------------------------------
with tabs[5]:
    st.header("Operational Integrity & Model Governance")
    st.caption("Provenance, data quality reports, and scientific boundaries from `AGENTS.md` and `MODEL_CARD.md`.")

    col_q1, col_q2 = st.columns(2)

    with col_q1:
        st.subheader("Data Quality Audit Report")
        if audit_report:
            st.json(audit_report)
        else:
            st.info("No data_quality_report.json found.")

    with col_q2:
        st.subheader("Ethical Safeguards & Constraints")
        st.markdown(
            """
            1. **No Imputed Zero Deaths**: Missing records preserved as `NaN`; never converted to zero deaths.
            2. **No Temporal Leakage**: Future observed weather and future target values are strictly barred from inference features.
            3. **Non-Causal Feature Attribution**: Feature importance represents associative model drivers, not clinical cause-and-effect.
            4. **Aggregated Demand Only**: Model outputs represent municipal hospital bed surge demand, not individual clinical diagnoses.
            """
        )
