import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from fastapi.testclient import TestClient
from app.config import settings
from fastapi import FastAPI

# Import all routers
from app.routers import (
    auth, transactions, categories, health, imports, reports, accounts, mappings
)

# Override settings for testing
settings.testing = True
settings.database_profile = "sqlite"

# Create a test engine and session
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def db_session_fixture():
    Base.metadata.create_all(bind=engine)  # Create tables
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)  # Drop tables after tests

@pytest.fixture(name="client")
def client_fixture(db_session: TestingSessionLocal):
    # Create a new FastAPI app instance for each test
    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        debug=settings.debug,
        description="Personal and Household Finance Management API - Refactored with layered architecture for better maintainability and performance."
    )

    # Include routers with /api prefix to maintain original API structure
    app.include_router(auth.router, prefix="/api")
    app.include_router(categories.router, prefix="/api")
    app.include_router(transactions.router, prefix="/api")
    app.include_router(accounts.router, prefix="/api")
    app.include_router(imports.router, prefix="/api")
    app.include_router(mappings.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(health.router, prefix="/api")

    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
