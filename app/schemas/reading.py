from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class MeterReadingBase(BaseModel):
    meter_id: int
    zone_id: int
    voltage: float = Field(..., gt=0, description="Voltage reading in Volts")
    current: float = Field(..., gt=0, description="Current reading in Amperes")
    power_consumption: float = Field(..., ge=0, description="Power consumption in kW")
    frequency: float = Field(..., gt=0, description="Frequency in Hz")
    temperature: float = Field(..., description="Temperature in Celsius")
    timestamp: datetime

class MeterReadingCreate(MeterReadingBase):
    pass

class MeterReadingResponse(MeterReadingBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

