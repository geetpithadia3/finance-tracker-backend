from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, User as UserResponse
from app import auth
from app.config import settings
from app.services.category_service import CategorySeedingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate, 
    db: Session = Depends(get_db)
):
    """Register a new user and automatically seed default categories"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    try:
        # Create user
        hashed_password = auth.get_password_hash(user.password)
        db_user = User(username=user.username, password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Automatically seed default categories for new user
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


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not auth.verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify")
def verify_auth(current_user: User = Depends(auth.get_current_user)):
    return {"status": "ok", "user_id": current_user.id}