from pydantic import BaseModel, ConfigDict
from typing import Optional

class MeterBase(BaseModel):
    serial_number: str
    zone_id: int
    status: Optional[str] = "active"
    capacity_limit_kw: float

class MeterCreate(MeterBase):
    pass

class MeterResponse(MeterBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

