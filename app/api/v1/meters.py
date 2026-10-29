from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.api import deps
from app.models.meter import Meter
from app.models.reading import MeterReading
from app.schemas.meter import MeterCreate, MeterResponse
from app.schemas.reading import MeterReadingCreate, MeterReadingResponse
from app.services.cache import cache_service

router = APIRouter()

@router.post("/", response_model=MeterResponse, status_code=status.HTTP_201_CREATED)
def create_meter(
    meter_in: MeterCreate,
    db: Session = Depends(deps.get_db),
    admin_user=Depends(deps.check_admin)
):
    """
    Register a new smart meter (Admin only).
    """
    meter_exists = db.query(Meter).filter(Meter.serial_number == meter_in.serial_number).first()
    if meter_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Smart meter with serial number '{meter_in.serial_number}' already registered."
        )
    
    db_meter = Meter(**meter_in.model_dump())
    db.add(db_meter)
    db.commit()
    db.refresh(db_meter)
    return db_meter

@router.get("/", response_model=List[MeterResponse])
def read_meters(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Retrieve all smart meters.
    """
    meters = db.query(Meter).offset(skip).limit(limit).all()
    return meters

@router.post("/readings", response_model=MeterReadingResponse, status_code=status.HTTP_201_CREATED)
def ingest_reading(
    reading_in: MeterReadingCreate,
    db: Session = Depends(deps.get_db)
):
    """
    Ingest a new telemetry reading from a smart meter.
    Also caches the latest reading in Redis for high-throughput reads.
    """
    # Verify meter exists
    meter = db.query(Meter).filter(Meter.id == reading_in.meter_id).first()
    if not meter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Smart meter with ID {reading_in.meter_id} does not exist."
        )

    db_reading = MeterReading(**reading_in.model_dump())
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    
    # Cache the latest reading details
    reading_dict = {
        "id": db_reading.id,
        "meter_id": db_reading.meter_id,
        "zone_id": db_reading.zone_id,
        "voltage": db_reading.voltage,
        "current": db_reading.current,
        "power_consumption": db_reading.power_consumption,
        "frequency": db_reading.frequency,
        "temperature": db_reading.temperature,
        "timestamp": db_reading.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    cache_service.set(f"latest_reading_meter_{db_reading.meter_id}", reading_dict, expire_seconds=86400)
    
    # Overload detection triggering in backend
    # If the reading exceeds 90% of the meter capacity, we can log it here.
    # Note: Celery also runs a periodic task every 2 minutes to check overload,
    # but immediate checks can trigger instantly here.
    if db_reading.power_consumption >= (meter.capacity_limit_kw * 0.9):
        # We can trigger alerts immediately or delegate to celery.
        # Let's write code to add the alert record to the DB.
        from app.models.alert import Alert
        alert = Alert(
            zone_id=meter.zone_id,
            meter_id=meter.id,
            alert_type="OVERLOAD",
            severity="CRITICAL" if db_reading.power_consumption >= meter.capacity_limit_kw else "WARNING",
            message=f"Smart Meter {meter.serial_number} exceeded 90% capacity! Load: {db_reading.power_consumption} kW / Limit: {meter.capacity_limit_kw} kW",
            timestamp=datetime.now(),
            resolved=False
        )
        db.add(alert)
        db.commit()

    return db_reading

@router.get("/readings", response_model=List[MeterReadingResponse])
def read_meter_readings(
    meter_id: int = None,
    zone_id: int = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Retrieve telemetry readings. Can be filtered by meter_id or zone_id.
    """
    query = db.query(MeterReading)
    if meter_id is not None:
        query = query.filter(MeterReading.meter_id == meter_id)
    if zone_id is not None:
        query = query.filter(MeterReading.zone_id == zone_id)
        
    readings = query.order_by(MeterReading.timestamp.desc()).offset(skip).limit(limit).all()
    return readings
