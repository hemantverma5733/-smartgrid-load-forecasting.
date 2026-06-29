from pydantic import BaseModel
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

    class Config:
        from_attributes = True
