from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.database import get_db
from app import models, schemas, auth
from app.config import settings
from app.services.category_service import CategorySeedingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=schemas.User)
def register(
    user: schemas.UserCreate, 
    seed_categories: bool = True,
    db: Session = Depends(get_db)
):
    """Register a new user with optional default category seeding"""
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    try:
        # Create user
        hashed_password = auth.get_password_hash(user.password)
        db_user = models.User(username=user.username, password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Seed default categories if requested
        if seed_categories:
            try:
                categories = CategorySeedingService.seed_default_categories(db, db_user.id)
                logger.info(f"Seeded {len(categories)} default categories for new user {db_user.username}")
            except Exception as e:
                logger.warning(f"Failed to seed categories for user {db_user.username}: {e}")
                # Don't fail registration if category seeding fails
        
        return db_user
        
    except Exception as e:
        logger.error(f"Error during user registration: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")


@router.post("/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == user_credentials.username).first()
    
    if not user or not auth.verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}