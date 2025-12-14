from pydantic_settings import BaseSettings
from typing import List
import os
import secrets
from pydantic import field_validator


class Settings(BaseSettings):
    # App settings
    app_name: str = "Finance Tracker API"
    version: str = "1.0.0"
    debug: bool = os.environ.get("DEBUG", "False").lower() == "true"
    testing: bool = os.environ.get("TESTING", "False").lower() == "true"
    
    # Database Profile (sqlite, postgresql)
    database_profile: str = "sqlite"
    
    # Database URLs for different profiles
    sqlite_database_url: str = "sqlite:///./finance_tracker.db"
    postgresql_database_url: str = "postgresql://user:password@localhost:5432/finance_tracker"
    
    # Security
    secret_key: str = os.environ.get("SECRET_KEY") or secrets.token_urlsafe(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173", "https://finance-tracker-frontend-7131.onrender.com"]
    
    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            # Handle wildcard case
            if v.strip() in ['["*"]', '["*"]', '*']:
                return ["*"]
            
            # Handle comma-separated string
            if ',' in v:
                return [origin.strip() for origin in v.split(',') if origin.strip()]
            
            # Handle single origin
            return [v.strip()] if v.strip() else []
        return v
    
    # PostgreSQL specific settings
    postgres_host: str = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_user: str = os.environ.get("POSTGRES_USER", "finance_user")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "finance_password")
    postgres_database: str = os.environ.get("POSTGRES_DATABASE", "finance_tracker")
    
    class Config:
        env_file = ".env"
    
    @property
    def database_url(self) -> str:
        """Get database URL based on the active profile"""
        if self.testing:
            return "sqlite:///./test.db"
        
        if self.database_profile.lower() == "postgresql":
            # Build PostgreSQL URL from components or use direct URL
            if hasattr(self, 'postgresql_database_url') and self.postgresql_database_url != "postgresql://user:password@localhost:5432/finance_tracker":
                return self.postgresql_database_url
            else:
                return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        else:
            # Default to SQLite
            return self.sqlite_database_url
    
    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database"""
        return self.database_profile.lower() == "sqlite"
    
    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database"""
        return self.database_profile.lower() == "postgresql"


settings = Settings()