from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Zone(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    capacity_limit_kw = Column(Float, nullable=False)

    meters = relationship("Meter", back_populates="zone", cascade="all, delete-orphan")
    readings = relationship("MeterReading", back_populates="zone", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="zone", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="zone", cascade="all, delete-orphan")
