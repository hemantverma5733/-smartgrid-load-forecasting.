from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Prediction(Base):
    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True)
    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=False)
    model_used = Column(String, nullable=False)
    predicted_load_kw = Column(Float, nullable=False)
    forecast_horizon_hours = Column(Integer, nullable=False)
    prediction_timestamp = Column(DateTime, nullable=False)
    target_timestamp = Column(DateTime, nullable=False)

    meter = relationship("Meter", back_populates="predictions")
    zone = relationship("Zone", back_populates="predictions")
