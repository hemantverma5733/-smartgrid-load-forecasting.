from pydantic import BaseModel, ConfigDict
from typing import Optional

class ZoneBase(BaseModel):
    name: str
    description: Optional[str] = None
    capacity_limit_kw: float

class ZoneCreate(ZoneBase):
    pass

class ZoneResponse(ZoneBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

