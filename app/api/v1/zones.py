from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.models.zone import Zone
from app.schemas.zone import ZoneCreate, ZoneResponse

router = APIRouter()

@router.post("/", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    zone_in: ZoneCreate,
    db: Session = Depends(deps.get_db),
    admin_user=Depends(deps.check_admin)
):
    """
    Create a new power grid zone (Admin only).
    """
    zone_exists = db.query(Zone).filter(Zone.name == zone_in.name).first()
    if zone_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Zone with name '{zone_in.name}' already exists."
        )
    
    db_zone = Zone(**zone_in.model_dump())
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

@router.get("/", response_model=List[ZoneResponse])
def read_zones(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Retrieve all power grid zones.
    """
    zones = db.query(Zone).offset(skip).limit(limit).all()
    return zones

@router.get("/{zone_id}", response_model=ZoneResponse)
def read_zone(
    zone_id: int,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user)
):
    """
    Get details of a specific zone.
    """
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )
    return zone
