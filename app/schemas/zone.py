from pydantic import BaseModel
from typing import Optional

class ZoneBase(BaseModel):
    name: str
    description: Optional[str] = None
    capacity_limit_kw: float

class ZoneCreate(ZoneBase):
    pass

class ZoneResponse(ZoneBase):
    id: int

    class Config:
        from_attributes = True
