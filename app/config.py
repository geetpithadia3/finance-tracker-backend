from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App settings
    app_name: str = "Finance Tracker API"
    version: str = "1.0.0"
    debug: bool = True
    
    # Database Profile (sqlite, postgresql)
    database_profile: str = "sqlite"
    
    # Database URLs for different profiles
    sqlite_database_url: str = "sqlite:///./finance_tracker.db"
    postgresql_database_url: str = "postgresql://user:password@localhost:5432/finance_tracker"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://finance-tracker-frontend-7131.onrender.com"
    ]
    
    # PostgreSQL specific settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "finance_user"
    postgres_password: str = "finance_password"
    postgres_database: str = "finance_tracker"
    
    class Config:
        env_file = ".env"
    
    @property
    def database_url(self) -> str:
        """Get database URL based on the active profile"""
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