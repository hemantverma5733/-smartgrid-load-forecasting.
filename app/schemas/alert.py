from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class AlertBase(BaseModel):
    zone_id: int
    meter_id: Optional[int] = None
    alert_type: str
    severity: str
    message: str
    timestamp: datetime
    resolved: bool = False

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

