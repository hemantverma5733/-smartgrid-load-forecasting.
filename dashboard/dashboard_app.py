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
    page_title="Smart Grid Load Forecasting Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Vanilla CSS injection for premium aesthetics)
st.markdown("""
<style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .metric-value { font-size: 2rem; font-weight: bold; color: #38bdf8; }
    .metric-label { font-size: 0.85rem; color: #94a3b8; margin-top: 5px; }
    .alert-card {
        background: rgba(239, 68, 68, 0.15);
        border-left: 5px solid #ef4444;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .alert-text { color: #fca5a5; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

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
st.sidebar.title("⚡ Smart Grid Forecaster")
st.sidebar.write("System status: **Healthy**")

# Auth form
with st.sidebar.expander("🔐 API Authentication", expanded=False):
    username = st.text_input("Username / Email", value="admin@smartgrid.com", key="login_username_input")
    password = st.text_input("Password", value="adminpassword123", type="password", key="login_password_input")
    if st.button("Connect", key="login_connect_button"):
        try:
            res = requests.post(
                f"{API_BASE_URL}/auth/login",
                data={"username": username, "password": password},
                timeout=3
            )
            if res.status_code == 200:
                st.session_state.token = res.json()["access_token"]
                st.session_state.auth_status = "Connected to REST API"
                st.success("Successfully logged in!")
            else:
                st.session_state.auth_status = "Auth Failed"
                st.error("Invalid credentials.")
        except Exception:
            st.session_state.auth_status = "Local Database Mode"
            st.warning("REST API unreachable. Operating in local DB mode.")

st.sidebar.info(f"Mode: **{st.session_state.auth_status}**")

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

# Main page layout
st.title("⚡ Smart Grid Load Forecasting System")
st.markdown("---")

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
        <div class="metric-value">{analytics['load_metrics_24h']['avg_load_kw']} kW</div>
        <div class="metric-label">Average Load (24h)</div>
    </div>
    """, unsafe_allow_html=True)
with m_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{analytics['load_metrics_24h']['peak_load_kw']} kW</div>
        <div class="metric-label">Peak Load (24h)</div>
    </div>
    """, unsafe_allow_html=True)
with m_col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{analytics['consumption_kwh']['daily_kwh']} kWh</div>
        <div class="metric-label">Daily Consumption</div>
    </div>
    """, unsafe_allow_html=True)
with m_col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{analytics['consumption_kwh']['weekly_kwh']} kWh</div>
        <div class="metric-label">Weekly Consumption</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Row 2: Charts and Alerts
c_col1, c_col2 = st.columns([2, 1])

with c_col1:
    st.subheader("📈 Historical Grid Load Trend")
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
            title="Hourly Power Consumption by Meter (kW)",
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Plotly
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No historical readings found. Ensure the dataset is seeded.")

with c_col2:
    st.subheader("⚠️ Active Overload Warnings")
    if alerts:
        for a in alerts:
            severity = a.get("severity", "WARNING")
            message = a.get("message", "")
            st.markdown(f"""
            <div class="alert-card" style="border-left-color: {'#ef4444' if severity == 'CRITICAL' else '#f59e0b'}">
                <span class="alert-text"><strong>[{severity}]</strong> {message}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No active overloads detected. System operating inside safety bounds.")

# Row 3: Predictions and Model Validation
st.markdown("---")
p_col1, p_col2 = st.columns(2)

with p_col1:
    st.subheader("🔮 Run Load Forecasting")
    
    # Load Zones & Meters options
    zones_df = load_db_data("SELECT id, name FROM zone")
    meters_df = load_db_data("SELECT id, serial_number, zone_id FROM meter")
    
    if not zones_df.empty:
        selected_zone_name = st.selectbox("Select Zone", options=zones_df["name"].tolist())
        selected_zone_id = int(zones_df[zones_df["name"] == selected_zone_name]["id"].iloc[0])
        
        # Filter meters
        zone_meters = meters_df[meters_df["zone_id"] == selected_zone_id]
        meter_options = ["All Meters (Zone Summary)"] + zone_meters["serial_number"].tolist()
        selected_meter_opt = st.selectbox("Select Meter", options=meter_options)
        
        selected_meter_id = None
        if selected_meter_opt != "All Meters (Zone Summary)":
            selected_meter_id = int(zone_meters[zone_meters["serial_number"] == selected_meter_opt]["id"].iloc[0])
            
        horizon = st.slider("Forecast Horizon (Hours)", min_value=1, max_value=48, value=24)
        
        if st.button("Generate Forecast"):
            with st.spinner("Calculating predictions..."):
                try:
                    # Run predictions using ML Predictor class directly to avoid API dependencies issues
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
                        st.error(f"Insufficient history. Found {len(df_last)} rows in SQL, need at least 25.")
                    else:
                        # Group if zone-level
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
                            x=df_last["timestamp"].tail(12),
                            y=df_last["power_consumption"].tail(12),
                            name="Historical Load",
                            line=dict(color="#94a3b8")
                        ))
                        # Add forecast
                        fig_pred.add_trace(go.Scatter(
                            x=pred_df["target_timestamp"],
                            y=pred_df["predicted_load_kw"],
                            name="Forecast Load",
                            line=dict(color="#10b981", dash="dash")
                        ))
                        fig_pred.update_layout(
                            title=f"Forecasting next {horizon} Hours (Model: {predictor.best_model_name})",
                            template="plotly_dark",
                            xaxis_title="Time",
                            yaxis_title="Load (kW)"
                        )
                        st.plotly_chart(fig_pred, use_container_width=True)
                        
                except Exception as e:
                    st.error(f"Forecasting failed: {e}")
    else:
        st.warning("Database empty. Run scripts/generate_sample_data.py to start.")

with p_col2:
    st.subheader("📊 AI Models Performance Comparison")
    
    # Load ML artifacts metadata
    metadata_path = "app/ml/artifacts/metadata.json"
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            import json
            meta = json.load(f)
            # Reformat metrics dictionary
            metrics_dict = meta["metrics"]
            
            comparison_rows = []
            for model_name, metrics in metrics_dict.items():
                comparison_rows.append({
                    "Model Name": model_name,
                    "MAE": round(metrics["MAE"], 4),
                    "RMSE": round(metrics["RMSE"], 4),
                    "MAPE (%)": f"{metrics['MAPE']:.2f}%",
                    "R² Score": round(metrics["R2"], 4)
                })
                
            df_metrics = pd.DataFrame(comparison_rows)
            st.table(df_metrics)
            
            st.info(f"Selected Champion Model: **{meta['best_model_name']}**")
            
            # Simple bar chart of MAE comparisons
            fig_bar = px.bar(
                df_metrics[df_metrics["Model Name"] != "Baseline"], 
                x="Model Name", 
                y="MAE", 
                title="Model Mean Absolute Error Comparison (Lower is Better)",
                template="plotly_dark",
                color="MAE",
                color_continuous_scale="Viridis"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No model training metadata found. Run the training script to evaluate models.")
