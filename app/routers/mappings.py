"""
Mappings Router (V2)
Manage Auto-Categorization Rules
"""
from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app import auth, schemas
from app.services.mapping_service import MappingService

router = APIRouter(
    prefix="/params/mappings", # Under params to signify configuration? Or just /mappings
    tags=["Mappings"],
    responses={404: {"description": "Not found"}},
)

# Use simple /mappings if preferred, but grouping configs is nice. Let's stick to /mappings for simplicity.
router = APIRouter(prefix="/mappings", tags=["Mappings"])

def get_mapping_service(db: Session = Depends(get_db)) -> MappingService:
    return MappingService(db)

@router.post("", response_model=schemas.MappingRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    rule_data: schemas.MappingRuleCreate,
    current_user: User = Depends(auth.get_current_user),
    service: MappingService = Depends(get_mapping_service)
):
    """Create a new auto-categorization rule"""
    if not current_user.party_id:
        raise HTTPException(status_code=400, detail="User has no party")

    return service.create_rule(
        current_user.party_id,
        rule_data.match_pattern,
        rule_data.target_category_id,
        rule_data.priority or 0
    )

@router.get("", response_model=List[schemas.MappingRuleResponse])
def get_rules(
    current_user: User = Depends(auth.get_current_user),
    service: MappingService = Depends(get_mapping_service)
):
    """Get all rules for the user"""
    if not current_user.party_id:
        return []
    return service.get_rules(current_user.party_id)

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str,
    current_user: User = Depends(auth.get_current_user),
    service: MappingService = Depends(get_mapping_service)
):
    """Delete a rule"""
    if not current_user.party_id:
        return
    service.delete_rule(rule_id, current_user.party_id)
