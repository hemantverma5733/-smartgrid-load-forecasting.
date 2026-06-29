from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Meter(Base):
    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String, unique=True, index=True, nullable=False)
    zone_id = Column(Integer, ForeignKey("zone.id"), nullable=False)
    status = Column(String, default="active")
    capacity_limit_kw = Column(Float, nullable=False)

    zone = relationship("Zone", back_populates="meters")
    readings = relationship("MeterReading", back_populates="meter", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="meter", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="meter", cascade="all, delete-orphan")
