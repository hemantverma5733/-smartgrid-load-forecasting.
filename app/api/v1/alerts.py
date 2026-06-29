from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.models.alert import Alert
from app.schemas.alert import AlertResponse

router = APIRouter()

@router.get("/", response_model=List[AlertResponse])
def get_active_alerts(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Get all active (unresolved) overload and temperature alerts.
    """
    alerts = db.query(Alert).filter(Alert.resolved == False).order_by(Alert.timestamp.desc()).all()
    return alerts

@router.get("/history", response_model=List[AlertResponse])
def get_alerts_history(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Get alert history (all logs).
    """
    alerts = db.query(Alert).order_by(Alert.timestamp.desc()).offset(skip).limit(limit).all()
    return alerts

@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Resolve an active warning or critical overload alert.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
        
    alert.resolved = True
    db.commit()
    db.refresh(alert)
    return alert
