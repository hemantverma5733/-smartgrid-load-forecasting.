from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class MeterReading(Base):
    id = Column(Integer, primary_key=True, index=True)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=False)
    voltage = Column(Float, nullable=False)
    current = Column(Float, nullable=False)
    power_consumption = Column(Float, nullable=False)  # in kW
    frequency = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)

    meter = relationship("Meter", back_populates="readings")
    zone = relationship("Zone", back_populates="readings")
