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
    
    if not category.is_editable:
        raise HTTPException(status_code=403, detail="This category cannot be edited")
    
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


@router.delete("/{category_id}")
def delete_category(
    category_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a category (only if it's editable)"""
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == current_user.id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if not category.is_editable:
        raise HTTPException(status_code=403, detail="This category cannot be deleted")
    
    # Check if category is in use by transactions
    transaction_count = db.query(models.Transaction).filter(
        models.Transaction.category_id == category_id
    ).count()
    
    if transaction_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category. It is used by {transaction_count} transaction(s)."
        )
    
    # Check if category is in use by recurring transactions
    recurring_count = db.query(models.RecurringTransaction).filter(
        models.RecurringTransaction.category_id == category_id
    ).count()
    
    if recurring_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category. It is used by {recurring_count} recurring transaction(s)."
        )
    
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}


@router.get("/defaults")
def get_default_categories_info() -> List[Dict[str, str]]:
    """Get information about available default categories without creating them"""
    return CategorySeedingService.get_default_categories_info()