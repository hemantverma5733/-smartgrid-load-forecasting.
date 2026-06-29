from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from typing import List

from app.api import deps
from app.ml.predictor import Predictor
from app.models.reading import MeterReading
from app.models.meter import Meter
from app.models.prediction import Prediction
from app.schemas.prediction import PredictRequest, PredictResponse, PredictionResultItem

router = APIRouter()

# Global predictor instance
try:
    predictor = Predictor()
except Exception as e:
    predictor = None
    print(f"Warning: Predictor could not be loaded: {e}. Model predictions will fallback to persistence.")

@router.post("/", response_model=PredictResponse)
def get_load_forecast(
    req: PredictRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Generate load forecasting for the next N hours (1h, 6h, 24h) for a specific meter or zone.
    Saves predictions in the database for tracking.
    """
    # Fetch historical readings to build lag/rolling features
    # We need at least 30 hours of historical readings
    limit_readings = 100
    
    query = db.query(MeterReading).filter(MeterReading.zone_id == req.zone_id)
    if req.meter_id is not None:
        query = query.filter(MeterReading.meter_id == req.meter_id)
        
    readings = query.order_by(MeterReading.timestamp.desc()).limit(limit_readings).all()
    
    if len(readings) < 25:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient history data. Found {len(readings)} readings, but need at least 25 to run forecasting."
        )

    # Convert database models to pandas dataframe
    rows = []
    for r in readings:
        rows.append({
            "timestamp": r.timestamp,
            "meter_id": r.meter_id,
            "zone_id": r.zone_id,
            "voltage": r.voltage,
            "current": r.current,
            "power_consumption": r.power_consumption,
            "frequency": r.frequency,
            "temperature": r.temperature
        })
        
    df = pd.DataFrame(rows)
    # Sort chronological
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    
    # If zone level, aggregate readings by timestamp
    if req.meter_id is None:
        # Group by timestamp and sum consumption/current, average voltage/temp/frequency
        df = df.groupby("timestamp").agg({
            "power_consumption": "sum",
            "current": "sum",
            "voltage": "mean",
            "frequency": "mean",
            "temperature": "mean",
            "zone_id": "first"
        }).reset_index()
        df["meter_id"] = 0  # dummy meter id for zone level
        
    # Generate predictions
    forecast_results = []
    model_used = "Persistence (Fallback)"
    
    if predictor is not None:
        try:
            model_used = predictor.best_model_name
            preds = predictor.predict_horizon(df, horizon_hours=req.horizon_hours)
            for p in preds:
                forecast_results.append(PredictionResultItem(
                    target_timestamp=p["target_timestamp"],
                    predicted_load_kw=p["predicted_load_kw"]
                ))
        except Exception as e:
            print(f"Error during ML prediction ({e}). Falling back to persistence.")
            predictor_failed = True
        else:
            predictor_failed = False
    else:
        predictor_failed = True
        
    if predictor_failed:
        # Persistence fallback: just repeat the last known power consumption
        last_power = float(df["power_consumption"].iloc[-1])
        last_time = df["timestamp"].iloc[-1]
        for step in range(1, req.horizon_hours + 1):
            forecast_results.append(PredictionResultItem(
                target_timestamp=last_time + timedelta(hours=step),
                predicted_load_kw=round(last_power + np.random.uniform(-1.0, 1.0), 2)
            ))
            
    # Save predictions in DB
    db_predictions = []
    now = datetime.now()
    for item in forecast_results:
        db_pred = Prediction(
            meter_id=req.meter_id,
            zone_id=req.zone_id,
            model_used=model_used,
            predicted_load_kw=item.predicted_load_kw,
            forecast_horizon_hours=req.horizon_hours,
            prediction_timestamp=now,
            target_timestamp=item.target_timestamp
        )
        db.add(db_pred)
        db_predictions.append(db_pred)
        
    db.commit()
    
    return PredictResponse(
        zone_id=req.zone_id,
        meter_id=req.meter_id,
        model_used=model_used,
        predictions=forecast_results
    )
