from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any

from app.api import deps
from app.models.reading import MeterReading
from app.models.meter import Meter
from app.models.zone import Zone
from app.services.cache import cache_service

router = APIRouter()

@router.get("/")
def get_grid_analytics(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Retrieve real-time power grid analytics.
    Results are cached for 5 minutes in Redis.
    """
    cache_key = "grid_analytics_summary"
    cached_data = cache_service.get(cache_key)
    if cached_data:
        return cached_data

    # Perform calculations on DB
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)
    
    # 1. Overall Load Metrics (last 24 hours)
    load_stats = db.query(
        func.avg(MeterReading.power_consumption),
        func.max(MeterReading.power_consumption),
        func.min(MeterReading.power_consumption)
    ).filter(MeterReading.timestamp >= one_day_ago).first()
    
    avg_load = round(float(load_stats[0] or 0.0), 2)
    peak_load = round(float(load_stats[1] or 0.0), 2)
    min_load = round(float(load_stats[2] or 0.0), 2)

    # 2. Consumption Estimates (Sum of power consumption over interval)
    # Since readings are hourly, the sum of power_consumption (kW) * 1 hour approximates energy in kWh
    daily_consumption = db.query(func.sum(MeterReading.power_consumption)).filter(
        MeterReading.timestamp >= one_day_ago
    ).scalar() or 0.0
    
    weekly_consumption = db.query(func.sum(MeterReading.power_consumption)).filter(
        MeterReading.timestamp >= one_week_ago
    ).scalar() or 0.0

    monthly_consumption = db.query(func.sum(MeterReading.power_consumption)).filter(
        MeterReading.timestamp >= one_month_ago
    ).scalar() or 0.0

    # 3. Zone-wise Consumption (last 24 hours)
    zone_stats = db.query(
        Zone.name,
        func.sum(MeterReading.power_consumption)
    ).join(MeterReading, Zone.id == MeterReading.zone_id).filter(
        MeterReading.timestamp >= one_day_ago
    ).group_by(Zone.name).all()
    
    zone_consumption = {name: round(float(val or 0.0), 2) for name, val in zone_stats}

    # 4. Top Energy Consumers (Meters - last 24 hours)
    top_meters = db.query(
        Meter.serial_number,
        func.sum(MeterReading.power_consumption)
    ).join(MeterReading, Meter.id == MeterReading.meter_id).filter(
        MeterReading.timestamp >= one_day_ago
    ).group_by(Meter.serial_number).order_by(
        func.sum(MeterReading.power_consumption).desc()
    ).limit(5).all()
    
    top_consumers = [{"serial_number": row[0], "consumption_kwh": round(float(row[1] or 0.0), 2)} for row in top_meters]

    # Combine into report
    analytics_report = {
        "calculated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "load_metrics_24h": {
            "avg_load_kw": avg_load,
            "peak_load_kw": peak_load,
            "min_load_kw": min_load
        },
        "consumption_kwh": {
            "daily_kwh": round(float(daily_consumption), 2),
            "weekly_kwh": round(float(weekly_consumption), 2),
            "monthly_kwh": round(float(monthly_consumption), 2)
        },
        "zone_consumption_24h": zone_consumption,
        "top_consumers_24h": top_consumers
    }

    # Cache response for 5 minutes (300 seconds)
    cache_service.set(cache_key, analytics_report, expire_seconds=300)
    
    return analytics_report
