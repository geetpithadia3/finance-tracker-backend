from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from app.database import get_db
from app import models, schemas, auth
from app.services.category_service import CategorySeedingService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=schemas.Category)
def create_category(
    category: schemas.CategoryCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_category = models.Category(**category.dict(), user_id=current_user.id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("", response_model=List[schemas.Category])
def list_categories(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Category).filter(models.Category.user_id == current_user.id).all()


@router.put("/{category_id}", response_model=schemas.Category)
def update_category(
    category_id: str,
    category_update: schemas.CategoryUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


@router.post("/seed", response_model=List[schemas.Category])
def seed_default_categories(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Seed default categories for the current user"""
    categories = CategorySeedingService.seed_default_categories(db, current_user.id)
    return categories


@router.post("/seed/custom", response_model=List[schemas.Category])
def seed_custom_categories(
    category_names: List[str],
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create custom categories for the current user"""
    categories = CategorySeedingService.seed_custom_categories(db, current_user.id, category_names)
    return categories


@router.get("/defaults")
def get_default_categories_info() -> List[Dict[str, str]]:
    """Get information about available default categories without creating them"""
    return CategorySeedingService.get_default_categories_info()