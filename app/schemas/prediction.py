from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class PredictionBase(BaseModel):
    meter_id: Optional[int] = None
    zone_id: int
    model_used: str
    predicted_load_kw: float
    forecast_horizon_hours: int
    prediction_timestamp: datetime
    target_timestamp: datetime

class PredictionCreate(PredictionBase):
    pass

class PredictionResponse(PredictionBase):
    id: int

    class Config:
        from_attributes = True

class PredictRequest(BaseModel):
    zone_id: int
    meter_id: Optional[int] = None
    horizon_hours: Optional[int] = 24  # Default 24 hours ahead

class PredictionResultItem(BaseModel):
    target_timestamp: datetime
    predicted_load_kw: float

class PredictResponse(BaseModel):
    zone_id: int
    meter_id: Optional[int] = None
    model_used: str
    predictions: List[PredictionResultItem]
