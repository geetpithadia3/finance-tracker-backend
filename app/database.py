from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sqlalchemy
import logging
from app.config import settings

logger = logging.getLogger(__name__)

def get_engine_config():
    """Get engine configuration based on database profile"""
    database_url = settings.database_url
    
    if settings.is_sqlite:
        # SQLite specific configuration
        return {
            "url": database_url,
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
            "echo": settings.debug
        }
    elif settings.is_postgresql:
        # PostgreSQL specific configuration
        return {
            "url": database_url,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "echo": settings.debug
        }
    else:
        # Fallback configuration
        logger.warning(f"Unknown database profile: {settings.database_profile}. Using default configuration.")
        return {
            "url": database_url,
            "echo": settings.debug
        }

# Create engine with profile-specific configuration
engine_config = get_engine_config()
engine = create_engine(**engine_config)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables"""
    logger.info(f"Creating tables for {settings.database_profile} database")
    logger.info(f"Database URL: {settings.database_url}")
    
    # Import models to ensure they're registered with Base
    from app import models
    
    logger.info(f"Creating tables: {list(Base.metadata.tables.keys())}")
    Base.metadata.create_all(bind=engine)


def check_database_connection():
    """Check if database connection is working"""
    try:
        with engine.connect() as connection:
            if settings.is_sqlite:
                result = connection.execute(sqlalchemy.text("SELECT 1"))
                result.fetchone()
            elif settings.is_postgresql:
                result = connection.execute(sqlalchemy.text("SELECT version()"))
                result.fetchone()
            logger.info(f"✅ Database connection successful ({settings.database_profile})")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_database_info():
    """Get information about the current database setup"""
    return {
        "profile": settings.database_profile,
        "url": settings.database_url.replace(settings.postgres_password, "****") if settings.is_postgresql else settings.database_url,
        "is_sqlite": settings.is_sqlite,
        "is_postgresql": settings.is_postgresql
    }