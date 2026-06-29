from datetime import datetime, timedelta
import json
import logging
from sqlalchemy import func

from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.models.alert import Alert
from app.models.report import AnalyticsReport
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

@celery_app.task
def monitor_grid_overloads():
    """
    Periodic task running every 30 seconds to audit latest smart meter telemetry
    and issue alerts if current load exceeds 90% of capacity.
    """
    logger.info("Auditing smart grid for overload conditions...")
    db = SessionLocal()
    try:
        meters = db.query(Meter).filter(Meter.status == "active").all()
        for meter in meters:
            # Try reading from cache first for performance
            cache_key = f"latest_reading_meter_{meter.id}"
            reading_data = cache_service.get(cache_key)
            
            if reading_data:
                power_consumption = reading_data["power_consumption"]
                timestamp_str = reading_data["timestamp"]
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            else:
                # Query database if cache is empty
                latest_reading = db.query(MeterReading).filter(
                    MeterReading.meter_id == meter.id
                ).order_by(MeterReading.timestamp.desc()).first()
                
                if not latest_reading:
                    continue
                power_consumption = latest_reading.power_consumption
                timestamp = latest_reading.timestamp

            # Check if load exceeds 90% capacity
            capacity_limit = meter.capacity_limit_kw
            threshold = capacity_limit * 0.9
            
            if power_consumption >= threshold:
                # Check if we generated an alert in the last 15 minutes for this meter to avoid flooding
                fifteen_minutes_ago = datetime.now() - timedelta(minutes=15)
                recent_alert = db.query(Alert).filter(
                    Alert.meter_id == meter.id,
                    Alert.alert_type == "OVERLOAD",
                    Alert.resolved == False,
                    Alert.timestamp >= fifteen_minutes_ago
                ).first()
                
                if not recent_alert:
                    severity = "CRITICAL" if power_consumption >= capacity_limit else "WARNING"
                    message = (
                        f"Smart Meter {meter.serial_number} load is at {power_consumption} kW, "
                        f"exceeding {90 if severity == 'WARNING' else 100}% capacity limit ({capacity_limit} kW)."
                    )
                    
                    alert = Alert(
                        zone_id=meter.zone_id,
                        meter_id=meter.id,
                        alert_type="OVERLOAD",
                        severity=severity,
                        message=message,
                        timestamp=datetime.now(),
                        resolved=False
                    )
                    db.add(alert)
                    db.commit()
                    logger.warning(f"ALERT GENERATED: {message}")
                    
                    # Clear dashboard/cached alerts so client re-fetches immediately
                    cache_service.delete("grid_analytics_summary")

    except Exception as e:
        logger.error(f"Error in grid monitoring task: {e}")
    finally:
        db.close()

@celery_app.task
def generate_grid_reports():
    """
    Periodic task to compile grid load analytics and serialize report summaries.
    """
    logger.info("Generating daily analytics report...")
    db = SessionLocal()
    try:
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        # Calculate stats
        total_meters = db.query(Meter).count()
        total_readings = db.query(MeterReading).filter(MeterReading.timestamp >= yesterday).count()
        
        load_stats = db.query(
            func.avg(MeterReading.power_consumption),
            func.max(MeterReading.power_consumption)
        ).filter(MeterReading.timestamp >= yesterday).first()
        
        avg_power = float(load_stats[0] or 0.0)
        peak_power = float(load_stats[1] or 0.0)
        
        total_alerts = db.query(Alert).filter(Alert.timestamp >= yesterday).count()
        
        report_data = {
            "interval_start": yesterday.strftime("%Y-%m-%d %H:%M:%S"),
            "interval_end": now.strftime("%Y-%m-%d %H:%M:%S"),
            "total_active_meters": total_meters,
            "total_telemetry_rows": total_readings,
            "average_grid_load_kw": round(avg_power, 2),
            "peak_grid_load_kw": round(peak_power, 2),
            "alerts_triggered": total_alerts
        }
        
        report = AnalyticsReport(
            generated_at=now,
            report_type="DAILY",
            data_json=json.dumps(report_data)
        )
        db.add(report)
        db.commit()
        logger.info(f"Daily report generated. ID: {report.id}")
        
    except Exception as e:
        logger.error(f"Error generating grid reports: {e}")
    finally:
        db.close()
