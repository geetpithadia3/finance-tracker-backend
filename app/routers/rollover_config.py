from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import RolloverConfig, Category, User
from app.auth import get_current_user

router = APIRouter(prefix="/rollover-config", tags=["rollover-config"])

@router.get("/{category_id}")
def get_rollover_config(
    category_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    config = db.query(RolloverConfig).filter(
        RolloverConfig.user_id == current_user.id,
        RolloverConfig.category_id == category_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Rollover config not found")
    return {
        "category_id": config.category_id,
        "rollover_enabled": config.rollover_enabled,
        "rollover_percentage": config.rollover_percentage,
        "max_rollover_amount": config.max_rollover_amount,
        "rollover_expiry_months": config.rollover_expiry_months,
    }

@router.put("/{category_id}")
def update_rollover_config(
    category_id: str,
    rollover_enabled: Optional[bool] = None,
    rollover_percentage: Optional[float] = None,
    max_rollover_amount: Optional[float] = None,
    rollover_expiry_months: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    config = db.query(RolloverConfig).filter(
        RolloverConfig.user_id == current_user.id,
        RolloverConfig.category_id == category_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Rollover config not found")
    if rollover_enabled is not None:
        config.rollover_enabled = rollover_enabled
    if rollover_percentage is not None:
        config.rollover_percentage = rollover_percentage
    if max_rollover_amount is not None:
        config.max_rollover_amount = max_rollover_amount
    if rollover_expiry_months is not None:
        config.rollover_expiry_months = rollover_expiry_months
    db.commit()
    db.refresh(config)
    return {
        "category_id": config.category_id,
        "rollover_enabled": config.rollover_enabled,
        "rollover_percentage": config.rollover_percentage,
        "max_rollover_amount": config.max_rollover_amount,
        "rollover_expiry_months": config.rollover_expiry_months,
    }

@router.post("/")
def create_rollover_config(
    category_id: str,
    rollover_enabled: bool = False,
    rollover_percentage: float = 100.0,
    max_rollover_amount: Optional[float] = None,
    rollover_expiry_months: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if config already exists
    existing = db.query(RolloverConfig).filter(
        RolloverConfig.user_id == current_user.id,
        RolloverConfig.category_id == category_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Rollover config already exists")
    config = RolloverConfig(
        user_id=current_user.id,
        category_id=category_id,
        rollover_enabled=rollover_enabled,
        rollover_percentage=rollover_percentage,
        max_rollover_amount=max_rollover_amount,
        rollover_expiry_months=rollover_expiry_months
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return {
        "category_id": config.category_id,
        "rollover_enabled": config.rollover_enabled,
        "rollover_percentage": config.rollover_percentage,
        "max_rollover_amount": config.max_rollover_amount,
        "rollover_expiry_months": config.rollover_expiry_months,
    } 