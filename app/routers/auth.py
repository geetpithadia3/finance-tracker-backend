from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, User as UserResponse
from app import auth
from app.config import settings
from app.services.auth_service import AuthService
from app.core.dependencies import get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate, 
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user and automatically seed default categories"""
    return auth_service.register_user(user)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.login_user(credentials)


@router.get("/verify")
def verify_auth(current_user: User = Depends(auth.get_current_user)):
    return {"status": "ok", "user_id": current_user.id}