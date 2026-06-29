from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Alert(Base):
    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=False)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True)
    alert_type = Column(String, nullable=False)  # "OVERLOAD", "VOLTAGE_DROP", "TEMPERATURE_HIGH", "OFFLINE"
    severity = Column(String, nullable=False)  # "WARNING", "CRITICAL"
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    resolved = Column(Boolean, default=False)

    zone = relationship("Zone", back_populates="alerts")
    meter = relationship("Meter", back_populates="alerts")
