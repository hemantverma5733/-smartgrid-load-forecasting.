import os
import sys
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User
from app.models.zone import Zone
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.core.security import get_password_hash

def generate_data():
    print("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(Zone).first():
            print("Database already seeded with zones. Skipping initial seeding...")
            return

        print("Seeding initial users, zones, and meters...")
        # Create default admin user
        admin = User(
            email="admin@smartgrid.com",
            hashed_password=get_password_hash("adminpassword123"),
            role="admin",
            is_active=True
        )
        db.add(admin)

        # Create zones
        zones_data = [
            {"name": "Residential Zone A", "description": "Residential area with high evening peak", "capacity_limit_kw": 200.0},
            {"name": "Industrial Zone B", "description": "Heavy industrial zone with constant daytime load", "capacity_limit_kw": 1000.0},
            {"name": "Commercial Zone C", "description": "Offices and shopping malls with daytime usage", "capacity_limit_kw": 500.0}
        ]
        
        zones = []
        for z in zones_data:
            zone = Zone(**z)
            db.add(zone)
            zones.append(zone)
        db.commit()

        # Create meters
        meters = []
        for i, zone in enumerate(zones):
            # Create 2 meters per zone
            for m_idx in range(1, 3):
                meter = Meter(
                    serial_number=f"MTR-{zone.name[0]}{zone.name[-1]}-{i}{m_idx:02d}",
                    zone_id=zone.id,
                    status="active",
                    capacity_limit_kw=zone.capacity_limit_kw * 0.45  # each meter takes ~45% of zone capacity
                )
                db.add(meter)
                meters.append(meter)
        db.commit()

        print(f"Created {len(zones)} zones and {len(meters)} meters.")
        
        # Generate historical readings (30 days of hourly data)
        print("Generating historical readings...")
        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)
        
        current_time = start_time
        readings_list = []
        csv_rows = []

        # Peak usage patterns by hour of day (0-23)
        # Residential: high peak at 19-21, small morning peak at 7-8
        res_profile = [0.3, 0.2, 0.2, 0.2, 0.3, 0.4, 0.6, 0.7, 0.5, 0.4, 0.4, 0.5, 0.6, 0.5, 0.4, 0.4, 0.5, 0.7, 0.9, 1.0, 0.9, 0.7, 0.5, 0.4]
        # Industrial: constant high from 8 to 17, low at night
        ind_profile = [0.15, 0.15, 0.15, 0.15, 0.2, 0.3, 0.6, 0.85, 0.9, 0.95, 0.95, 0.9, 0.9, 0.95, 0.95, 0.9, 0.85, 0.6, 0.3, 0.2, 0.2, 0.15, 0.15, 0.15]
        # Commercial: high peak 9 to 18
        com_profile = [0.2, 0.15, 0.15, 0.15, 0.2, 0.3, 0.5, 0.7, 0.85, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.85, 0.7, 0.5, 0.4, 0.3, 0.25, 0.2, 0.2]

        profiles = {
            "Residential Zone A": res_profile,
            "Industrial Zone B": ind_profile,
            "Commercial Zone C": com_profile
        }

        while current_time <= end_time:
            hour = current_time.hour
            weekday = current_time.weekday()
            
            # Simple daily temperature cycle
            # peak temperature at 15:00, coolest at 05:00
            temp_base = 25.0
            temp_cycle = 8.0 * np.sin((hour - 9) * 2 * np.pi / 24)
            temperature = temp_base + temp_cycle + random.uniform(-1.5, 1.5)

            # Weekend factor (lower industrial/commercial, slightly higher residential)
            is_weekend = 1 if weekday >= 5 else 0

            for meter in meters:
                zone_name = meter.zone.name
                profile = profiles[zone_name]
                
                # Base factor
                load_factor = profile[hour]
                
                # Weekend discount
                if is_weekend:
                    if "Industrial" in zone_name:
                        load_factor *= 0.3
                    elif "Commercial" in zone_name:
                        load_factor *= 0.5
                    elif "Residential" in zone_name:
                        load_factor *= 1.1

                # Temperature impact (high temperature leads to cooling load)
                temp_factor = 1.0
                if temperature > 28.0:
                    temp_factor += (temperature - 28.0) * 0.05  # 5% increase per degree above 28

                # Calculate final power consumption
                max_consumption = meter.capacity_limit_kw * 0.8
                power = max_consumption * load_factor * temp_factor + random.uniform(-2.0, 2.0)
                power = max(0.5, power)  # minimum load of 0.5 kW

                # Calculate voltage and current
                # Voltage: average 220V with slight fluctuations
                voltage = 220.0 + random.uniform(-4.0, 4.0)
                
                # Power (W) = V * I * pf -> I = (Power * 1000) / (V * pf)
                # Assume power factor pf = 0.9
                pf = 0.9
                current = (power * 1000.0) / (voltage * pf)
                
                frequency = 50.0 + random.uniform(-0.15, 0.15)
                
                # Create reading
                reading = MeterReading(
                    meter_id=meter.id,
                    zone_id=meter.zone_id,
                    voltage=round(voltage, 2),
                    current=round(current, 2),
                    power_consumption=round(power, 2),
                    frequency=round(frequency, 2),
                    temperature=round(temperature, 2),
                    timestamp=current_time
                )
                db.add(reading)
                
                # Add to CSV rows
                csv_rows.append({
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "meter_id": meter.id,
                    "serial_number": meter.serial_number,
                    "zone_id": meter.zone_id,
                    "zone_name": zone_name,
                    "voltage": round(voltage, 2),
                    "current": round(current, 2),
                    "power_consumption": round(power, 2),
                    "frequency": round(frequency, 2),
                    "temperature": round(temperature, 2),
                })
            
            # Commit in batches of 100 hours to avoid memory build-up
            if len(csv_rows) % (len(meters) * 100) == 0:
                db.commit()
                print(f"Generated data up to {current_time}")

            current_time += timedelta(hours=1)
            
        db.commit()
        print("Database successfully seeded.")
        
        # Save to CSV
        os.makedirs("data", exist_ok=True)
        csv_path = "data/sample_meter_data.csv"
        df = pd.DataFrame(csv_rows)
        df.to_csv(csv_path, index=False)
        print(f"Saved synthetic dataset of {len(df)} rows to {csv_path}")
        
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    generate_data()
