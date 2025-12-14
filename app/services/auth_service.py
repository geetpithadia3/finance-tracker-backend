from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.models import User
from app.schemas import UserCreate, UserLogin, Token
from app import auth
from app.config import settings
from app.services.category_service import CategoryService
from app.services.ledger_service import LedgerService
from app.core.error_handler import raise_http_exception

logger = logging.getLogger("finance_tracker.auth")

class AuthService:
    def __init__(self, db: Session, category_service: CategoryService, ledger_service: LedgerService):
        self.db = db
        self.category_service = category_service
        self.ledger_service = ledger_service

    def register_user(self, user_data: UserCreate) -> User:
        logger.info(f"Attempting to register user: {user_data.username}")
        existing_user = self.db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            logger.warning(f"Registration failed: Username {user_data.username} already exists")
            raise_http_exception(status_code=400, detail="Username already registered")
        
        try:
            # V2: Create Party first
            party = self.ledger_service.create_party("USER", user_data.username)
            
            hashed_password = auth.get_password_hash(user_data.password)
            db_user = User(username=user_data.username, password=hashed_password, party_id=party.id)
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            
            try:
                # V1 Seeding
                categories = self.category_service.seed_default_categories(db_user)
                
                # V2 Seeding
                self.ledger_service.seed_default_accounts(party.id)
                logger.info(f"Seeded V2 accounts for party {party.name}")
                
                logger.info(f"Seeded {len(categories)} default categories for new user {db_user.username}")
            except Exception as e:
                logger.warning(f"Failed to seed categories/accounts for user {db_user.username}: {e}")
            
            logger.info(f"Successfully registered user: {db_user.username} with party_id: {party.id}")
            return db_user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error during user registration: {e}")
            raise_http_exception(status_code=500, detail="Registration failed")

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        logger.info(f"Authentication attempt for user: {username}")
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            logger.warning(f"Authentication failed: User {username} not found")
            return None
        if not auth.verify_password(password, user.password):
            logger.warning(f"Authentication failed: Invalid password for user {username}")
            return None
        logger.info(f"Successfully authenticated user: {username}")
        return user

    def login_user(self, credentials: UserLogin) -> Token:
        user = self.db.query(User).filter(User.username == credentials.username).first()
        
        if not user or not auth.verify_password(credentials.password, user.password):
            raise_http_exception(
                status_code=401,
                detail="Incorrect username or password"
            )
        
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = auth.create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
