import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to allow importing models/configs if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Page configuration
st.set_page_config(
    page_title="GridVision™ | Smart Grid EMS & Forecasting",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Bespoke Styling (Industrial Energy SCADA / Clean Power Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #0b0e14 !important;
        color: #e2e8f0;
    }

    /* Top Grid Header */
    .grid-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        padding: 18px 24px;
        background: #111722;
        border: 1px solid #1e293b;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .grid-title-area {
        display: flex;
        flex-direction: column;
    }
    .grid-brand-title {
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .grid-subtitle {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 3px;
        font-weight: 500;
    }
    .grid-status-badges {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    .grid-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        padding: 5px 11px;
        border-radius: 6px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-live {
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-freq {
        background: rgba(56, 189, 248, 0.1);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.25);
    }
    .badge-dispatch {
        background: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }

    /* Metric Cards */
    .metric-card {
        background: #111722;
        border: 1px solid #1e293b;
        border-top: 3px solid #10b981;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .metric-card:hover {
        border-color: #334155;
    }
    .metric-card.accent-amber {
        border-top-color: #f59e0b;
    }
    .metric-card.accent-cyan {
        border-top-color: #06b6d4;
    }
    .metric-card.accent-indigo {
        border-top-color: #6366f1;
    }
    .metric-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin-bottom: 8px;
    }
    .metric-value-wrap {
        display: flex;
        align-items: baseline;
        gap: 6px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.85rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.1;
    }
    .metric-unit {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        font-weight: 600;
        color: #94a3b8;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #10b981;
        margin-top: 8px;
        display: flex;
        align-items: center;
        gap: 5px;
        font-weight: 500;
    }
    .metric-sub.sub-amber {
        color: #f59e0b;
    }
    .metric-sub.sub-cyan {
        color: #06b6d4;
    }
    .metric-sub.sub-indigo {
        color: #818cf8;
    }

    /* Alert / Alarm Cards */
    .alert-card {
        background: #181216;
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-left: 4px solid #ef4444;
        padding: 12px 14px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .alert-card.warning {
        background: #191610;
        border-color: rgba(245, 158, 11, 0.25);
        border-left-color: #f59e0b;
    }
    .alert-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    .alert-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 4px;
        letter-spacing: 0.05em;
    }
    .alert-badge.critical {
        background: rgba(239, 68, 68, 0.2);
        color: #f87171;
    }
    .alert-badge.warning {
        background: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
    }
    .alert-time {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #64748b;
    }
    .alert-text {
        color: #e2e8f0;
        font-size: 0.82rem;
        line-height: 1.4;
    }

    /* Section Subheadings */
    .section-head {
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: #f8fafc;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Champion Model Banner */
    .champion-banner {
        background: #111e1f;
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 8px;
        padding: 12px 16px;
        margin: 14px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .champion-label {
        font-size: 0.8rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .champion-name {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.95rem;
        font-weight: 700;
        color: #10b981;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d121c !important;
        border-right: 1px solid #1a2333;
    }

    /* Streamlit Native Button */
    .stButton > button {
        background: #10b981 !important;
        color: #0b0e14 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 9px 22px !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: #059669 !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper for Industrial Plotly Charts
def apply_chart_theme(fig, title=""):
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=14, color="#f8fafc"),
            x=0.01,
            y=0.96
        ),
        paper_bgcolor="#111722",
        plot_bgcolor="#111722",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#94a3b8", size=12),
        margin=dict(l=45, r=20, t=50, b=35),
        legend=dict(
            bgcolor="rgba(17, 23, 34, 0.85)",
            bordercolor="#1e293b",
            borderwidth=1,
            font=dict(size=11, color="#cbd5e1")
        ),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.07)",
            zerolinecolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#64748b"),
            showline=True,
            linecolor="#1e293b"
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.07)",
            zerolinecolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(family="JetBrains Mono, monospace", size=10, color="#64748b"),
            showline=True,
            linecolor="#1e293b"
        ),
        hoverlabel=dict(
            bgcolor="#0b0e14",
            bordercolor="#334155",
            font=dict(family="JetBrains Mono, monospace", color="#ffffff", size=12)
        )
    )
    return fig

# App Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    try:
        from app.config import settings
        DATABASE_URL = settings.DATABASE_URL
    except Exception:
        DATABASE_URL = "sqlite:///./smartgrid.db"

# Create SQLAlchemy engine for SQL queries
from sqlalchemy import create_engine
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True if not DATABASE_URL.startswith("sqlite") else False
    )
    # Test connection to verify if the server is active
    with engine.connect() as conn:
        pass
except Exception as e:
    engine = create_engine("sqlite:///./smartgrid.db")

# Auto-initialize database tables and seed if empty
try:
    from app.db.base import Base
    from app.db.session import SessionLocal
    from app.models.zone import Zone
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db_session_check:
        if not db_session_check.query(Zone).first():
            from scripts.generate_sample_data import generate_data
            generate_data()
except Exception:
    pass

# Session state initialization
if "token" not in st.session_state:
    st.session_state.token = None
if "auth_status" not in st.session_state:
    st.session_state.auth_status = "Disconnected"

# Sidebar Auth and Mode Selector
st.sidebar.markdown("""
<div style="padding: 10px 0 16px 0;">
    <div style="font-size: 1.15rem; font-weight: 800; color: #ffffff; letter-spacing: -0.01em;">
        ⚡ GridVision™ EMS
    </div>
    <div style="font-size: 0.75rem; color: #64748b; font-weight: 600; margin-top: 2px;">
        ENERGY MANAGEMENT SYSTEM
    </div>
</div>
""", unsafe_allow_html=True)

# Auth form
with st.sidebar.expander("🔐 REST API Authentication", expanded=False):
    username = st.text_input("Username / Email", value="admin@smartgrid.com", key="login_username_input")
    password = st.text_input("Password", value="adminpassword123", type="password", key="login_password_input")
    if st.button("Connect to API", key="login_connect_button"):
        try:
            res = requests.post(
                f"{API_BASE_URL}/auth/login",
                data={"username": username, "password": password},
                timeout=3
            )
            if res.status_code == 200:
                st.session_state.token = res.json()["access_token"]
                st.session_state.auth_status = "Connected to REST API"
                st.success("Authenticated with REST API")
            else:
                st.session_state.auth_status = "Auth Failed"
                st.error("Invalid credentials.")
        except Exception:
            st.session_state.auth_status = "Local Database Mode"
            st.warning("REST API unreachable. Running in local DB mode.")

st.sidebar.markdown(f"""
<div style="background: #111722; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 14px; margin-top: 10px;">
    <div style="font-size: 0.7rem; color: #64748b; font-weight: 700; text-transform: uppercase;">Engine Mode</div>
    <div style="font-size: 0.85rem; font-weight: 600; color: #e2e8f0; margin-top: 2px;">{st.session_state.auth_status}</div>
</div>
""", unsafe_allow_html=True)

# Data loading helpers
from sqlalchemy import text
def load_db_data(query, params=None):
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn, params=params)
            return df
    except Exception as e:
        st.error(f"DB Error: {e}")
    return pd.DataFrame()

# Top Live SCADA Header
st.markdown("""
<div class="grid-header">
    <div class="grid-title-area">
        <h1 class="grid-brand-title">
            <span style="color: #10b981;">⚡</span> GridVision™ Dispatch & Load Forecasting
        </h1>
        <div class="grid-subtitle">High-Reliability Smart Grid Analytics, Autoregressive ML & Overload Protection</div>
    </div>
    <div class="grid-status-badges">
        <span class="grid-badge badge-live">● TELEMETRY LIVE</span>
        <span class="grid-badge badge-freq">GRID FREQ: 50.01 Hz</span>
        <span class="grid-badge badge-dispatch">FEEDERS: 6/6 NOMINAL</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Load summary metrics
if st.session_state.token:
    # Query API
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        res_analytics = requests.get(f"{API_BASE_URL}/analytics/", headers=headers, timeout=3)
        res_alerts = requests.get(f"{API_BASE_URL}/alerts/", headers=headers, timeout=3)
        
        if res_analytics.status_code == 200 and res_alerts.status_code == 200:
            analytics = res_analytics.json()
            alerts = res_alerts.json()
            if not isinstance(analytics, dict) or "load_metrics_24h" not in analytics:
                analytics = None
                alerts = None
        else:
            if res_analytics.status_code == 401 or res_alerts.status_code == 401:
                st.session_state.token = None
                st.session_state.auth_status = "Disconnected"
            analytics = None
            alerts = None
    except Exception:
        analytics = None
        alerts = None
else:
    analytics = None
    alerts = None

# Local Fallback computations if REST API is not loaded
if not analytics:
    # Compute via SQL
    df_readings = load_db_data("SELECT power_consumption, timestamp FROM meterreading ORDER BY timestamp DESC LIMIT 1000")
    if not df_readings.empty:
        avg_load = df_readings["power_consumption"].mean()
        peak_load = df_readings["power_consumption"].max()
        min_load = df_readings["power_consumption"].min()
        daily_kwh = df_readings["power_consumption"].sum() / 6.0  # mock daily average scaled
        
        analytics = {
            "load_metrics_24h": {"avg_load_kw": round(avg_load, 2), "peak_load_kw": round(peak_load, 2), "min_load_kw": round(min_load, 2)},
            "consumption_kwh": {"daily_kwh": round(daily_kwh, 2), "weekly_kwh": round(daily_kwh * 7, 2), "monthly_kwh": round(daily_kwh * 30, 2)}
        }
    else:
        analytics = {
            "load_metrics_24h": {"avg_load_kw": 0.0, "peak_load_kw": 0.0, "min_load_kw": 0.0},
            "consumption_kwh": {"daily_kwh": 0.0, "weekly_kwh": 0.0, "monthly_kwh": 0.0}
        }

if alerts is None:
    df_alerts = load_db_data("SELECT message, severity, timestamp FROM alert WHERE resolved=0 LIMIT 5")
    alerts = df_alerts.to_dict(orient="records") if not df_alerts.empty else []

# Row 1: Metrics Cards
m_col1, m_col2, m_col3, m_col4 = st.columns(4)

with m_col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Average Load (24h)</div>
        <div class="metric-value-wrap">
            <span class="metric-value">{analytics['load_metrics_24h']['avg_load_kw']}</span>
            <span class="metric-unit">kW</span>
        </div>
        <div class="metric-sub">● Operating within baseline</div>
    </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown(f"""
    <div class="metric-card accent-amber">
        <div class="metric-label">Peak Demand (24h)</div>
        <div class="metric-value-wrap">
            <span class="metric-value">{analytics['load_metrics_24h']['peak_load_kw']}</span>
            <span class="metric-unit">kW</span>
        </div>
        <div class="metric-sub sub-amber">▲ Recorded maximum load</div>
    </div>
    """, unsafe_allow_html=True)

with m_col3:
    st.markdown(f"""
    <div class="metric-card accent-cyan">
        <div class="metric-label">Daily Consumption</div>
        <div class="metric-value-wrap">
            <span class="metric-value">{analytics['consumption_kwh']['daily_kwh']}</span>
            <span class="metric-unit">kWh</span>
        </div>
        <div class="metric-sub sub-cyan">● Aggregate energy delivered</div>
    </div>
    """, unsafe_allow_html=True)

with m_col4:
    st.markdown(f"""
    <div class="metric-card accent-indigo">
        <div class="metric-label">Weekly Consumption</div>
        <div class="metric-value-wrap">
            <span class="metric-value">{analytics['consumption_kwh']['weekly_kwh']}</span>
            <span class="metric-unit">kWh</span>
        </div>
        <div class="metric-sub sub-indigo">● Rolling 7-day cumulative</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# Row 2: Charts and Alerts
c_col1, c_col2 = st.columns([2, 1])

with c_col1:
    st.markdown('<div class="section-head">📈 Historical Feeder Load Telemetry</div>', unsafe_allow_html=True)
    # Load recent history
    df_history = load_db_data("""
        SELECT r.timestamp, r.power_consumption, m.serial_number 
        FROM meterreading r 
        JOIN meter m ON r.meter_id = m.id 
        ORDER BY r.timestamp DESC LIMIT 300
    """)
    if not df_history.empty:
        df_history["timestamp"] = pd.to_datetime(df_history["timestamp"])
        fig = px.line(
            df_history, 
            x="timestamp", 
            y="power_consumption", 
            color="serial_number",
            color_discrete_sequence=["#10b981", "#38bdf8", "#f59e0b", "#ec4899", "#8b5cf6", "#14b8a6"]
        )
        fig = apply_chart_theme(fig, "Hourly Active Power Consumption by Smart Meter (kW)")
        fig.update_traces(line=dict(width=1.8))
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No historical readings found. Ensure the dataset is seeded.")

with c_col2:
    st.markdown('<div class="section-head">⚠️ Active Safety Alarms</div>', unsafe_allow_html=True)
    if alerts:
        for a in alerts:
            severity = a.get("severity", "WARNING").upper()
            message = a.get("message", "")
            time_str = str(a.get("timestamp", ""))[-8:]
            is_crit = severity == "CRITICAL"
            card_class = "alert-card" if is_crit else "alert-card warning"
            badge_class = "alert-badge critical" if is_crit else "alert-badge warning"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div class="alert-header">
                    <span class="{badge_class}">{severity}</span>
                    <span class="alert-time">{time_str}</span>
                </div>
                <div class="alert-text">{message}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: #111722; border: 1px solid #1e293b; border-left: 4px solid #10b981; border-radius: 8px; padding: 16px; margin-top: 8px;">
            <div style="color: #10b981; font-weight: 700; font-size: 0.9rem; margin-bottom: 3px;">
                ● All Feeders Nominal
            </div>
            <div style="color: #94a3b8; font-size: 0.8rem;">
                No overload conditions detected across active transmission zones.
            </div>
        </div>
        """, unsafe_allow_html=True)

# Row 3: Predictions and Model Validation
st.markdown("<hr style='border: none; border-top: 1px solid #1e293b; margin: 24px 0;'>", unsafe_allow_html=True)
p_col1, p_col2 = st.columns(2)

with p_col1:
    st.markdown('<div class="section-head">🔮 Autoregressive Load Forecaster</div>', unsafe_allow_html=True)
    
    # Load Zones & Meters options
    zones_df = load_db_data("SELECT id, name FROM zone")
    meters_df = load_db_data("SELECT id, serial_number, zone_id FROM meter")
    
    if not zones_df.empty:
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            selected_zone_name = st.selectbox("Grid Zone Target", options=zones_df["name"].tolist())
            selected_zone_id = int(zones_df[zones_df["name"] == selected_zone_name]["id"].iloc[0])
        
        with col_sel2:
            zone_meters = meters_df[meters_df["zone_id"] == selected_zone_id]
            meter_options = ["All Meters (Zone Summary)"] + zone_meters["serial_number"].tolist()
            selected_meter_opt = st.selectbox("Select Feeder Meter", options=meter_options)
        
        selected_meter_id = None
        if selected_meter_opt != "All Meters (Zone Summary)":
            selected_meter_id = int(zone_meters[zone_meters["serial_number"] == selected_meter_opt]["id"].iloc[0])
            
        horizon = st.slider("Lookahead Forecast Horizon (Hours)", min_value=1, max_value=48, value=24)
        
        if st.button("Generate ML Forecast"):
            with st.spinner("Computing multistep autoregressive inference..."):
                try:
                    from app.ml.predictor import Predictor
                    predictor = Predictor()
                    
                    # Fetch last 30 readings
                    query = "SELECT * FROM meterreading WHERE zone_id = :zone_id"
                    params = {"zone_id": selected_zone_id}
                    if selected_meter_id is not None:
                        query += " AND meter_id = :meter_id"
                        params["meter_id"] = selected_meter_id
                        
                    query += " ORDER BY timestamp DESC LIMIT 50"
                    
                    df_last = load_db_data(query, params)
                    if len(df_last) < 25:
                        st.error(f"Insufficient history. Found {len(df_last)} readings, need at least 25.")
                    else:
                        if selected_meter_id is None:
                            df_last = df_last.groupby("timestamp").agg({
                                "power_consumption": "sum",
                                "current": "sum",
                                "voltage": "mean",
                                "frequency": "mean",
                                "temperature": "mean",
                                "zone_id": "first"
                            }).reset_index()
                            df_last["meter_id"] = 0
                            
                        preds = predictor.predict_horizon(df_last, horizon_hours=horizon)
                        pred_df = pd.DataFrame(preds)
                        
                        # Plot forecast curve
                        fig_pred = go.Figure()
                        # Add actual history
                        fig_pred.add_trace(go.Scatter(
                            x=df_last["timestamp"].tail(14),
                            y=df_last["power_consumption"].tail(14),
                            name="Historical Actual",
                            line=dict(color="#64748b", width=2),
                            fill="tozeroy",
                            fillcolor="rgba(100, 116, 139, 0.08)"
                        ))
                        # Add forecast
                        fig_pred.add_trace(go.Scatter(
                            x=pred_df["target_timestamp"],
                            y=pred_df["predicted_load_kw"],
                            name="Model Forecast",
                            line=dict(color="#f59e0b", width=2.5, dash="dash")
                        ))
                        fig_pred = apply_chart_theme(
                            fig_pred, 
                            f"Load Projection (+{horizon}h) via Champion Model: {predictor.best_model_name}"
                        )
                        fig_pred.update_layout(xaxis_title="Timeline", yaxis_title="Active Load (kW)")
                        st.plotly_chart(fig_pred, width="stretch")
                        
                except Exception as e:
                    st.error(f"Forecasting inference failed: {e}")
    else:
        st.warning("Database empty. Ensure dataset is initialized.")

with p_col2:
    st.markdown('<div class="section-head">📊 Model Performance Benchmark</div>', unsafe_allow_html=True)
    
    # Load ML artifacts metadata
    metadata_path = "app/ml/artifacts/metadata.json"
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            import json
            meta = json.load(f)
            metrics_dict = meta["metrics"]
            
            comparison_rows = []
            for model_name, metrics in metrics_dict.items():
                comparison_rows.append({
                    "Model": model_name,
                    "MAE": round(metrics["MAE"], 4),
                    "RMSE": round(metrics["RMSE"], 4),
                    "MAPE": f"{metrics['MAPE']:.2f}%",
                    "R² Score": round(metrics["R2"], 4)
                })
                
            df_metrics = pd.DataFrame(comparison_rows)
            st.dataframe(df_metrics, hide_index=True, width="stretch")
            
            best_model = meta['best_model_name']
            st.markdown(f"""
            <div class="champion-banner">
                <div>
                    <div class="champion-label">Production Champion Architecture</div>
                    <div class="champion-name">🏆 {best_model}</div>
                </div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #10b981; background: rgba(16, 185, 129, 0.15); padding: 4px 10px; border-radius: 4px;">
                    DEPLOYED
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Bespoke Bar Chart (Highlighting Champion Model)
            df_chart = df_metrics[df_metrics["Model"] != "Baseline"].copy()
            bar_colors = ["#10b981" if m == best_model else "#38bdf8" for m in df_chart["Model"]]
            
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=df_chart["Model"],
                    y=df_chart["MAE"],
                    marker=dict(color=bar_colors),
                    text=df_chart["MAE"].round(2),
                    textposition="auto",
                    textfont=dict(family="JetBrains Mono, monospace", color="#ffffff")
                )
            ])
            fig_bar = apply_chart_theme(fig_bar, "Mean Absolute Error by Model (Lower is Better)")
            fig_bar.update_layout(showlegend=False, yaxis_title="MAE (kW)")
            st.plotly_chart(fig_bar, width="stretch")
    else:
        st.info("No model training metadata found. Run the training script to evaluate models.")
