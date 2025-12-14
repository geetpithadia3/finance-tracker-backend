"""
Refactored categories router using the new layered architecture
Maintains original API paths for backwards compatibility
"""
from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from app import schemas, auth
from app.models import User
from app.services.category_service import CategoryService
from app.core.dependencies import get_category_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=schemas.Category, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: schemas.CategoryCreate,
    current_user: User = Depends(auth.get_current_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Create a new category"""
    return category_service.create_category(category_data, current_user)


@router.get("", response_model=List[schemas.Category])
def get_categories(
    current_user: User = Depends(auth.get_current_user),
    category_service: CategoryService = Depends(get_category_service),
    household_id: Optional[str] = Query(None, description="Filter by household"),
    include_household: bool = Query(True, description="Include household categories"),
    show_usage_stats: bool = Query(False, description="Include usage statistics")
):
    """Get user categories with optional household categories"""
    return category_service.get_user_categories(
        current_user, household_id, include_household, show_usage_stats
    )


@router.get("/{category_id}", response_model=schemas.Category)
def get_category(
    category_id: str,
    current_user: User = Depends(auth.get_current_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Get a specific category"""
    return category_service.get_category_by_id(category_id, current_user)

# Keep seed for potential utility, but simplified
@router.post("/seed", response_model=List[schemas.Category], status_code=status.HTTP_201_CREATED)
def seed_default_categories(
    current_user: User = Depends(auth.get_current_user),
    category_service: CategoryService = Depends(get_category_service)
):
    """Seed default categories for the current user"""
    return category_service.seed_default_categories(current_user)
