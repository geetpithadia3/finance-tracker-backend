#!/usr/bin/env python3
"""
Setup script for development data - creates user and categories for testing budget plans
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import User, Category
from app.services.category_service import CategorySeedingService
from sqlalchemy.orm import Session

def setup_dev_data():
    """Setup development data"""
    
    db = SessionLocal()
    
    try:
        # Check if user exists
        user = db.query(User).first()
        if not user:
            print("Creating default development user...")
            user = User(
                username="dev_user",
                password="hashed_password_placeholder",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created user: {user.username} (ID: {user.id})")
        else:
            print(f"✅ User exists: {user.username} (ID: {user.id})")
        
        # Check if categories exist for this user
        user_categories = db.query(Category).filter(Category.user_id == user.id).all()
        if not user_categories:
            print("Creating default categories...")
            categories = CategorySeedingService.seed_default_categories(db, user.id)
            print(f"✅ Created {len(categories)} default categories")
            for cat in categories[:5]:  # Show first 5
                print(f"  - {cat.name} (ID: {cat.id})")
            if len(categories) > 5:
                print(f"  ... and {len(categories) - 5} more")
        else:
            print(f"✅ User has {len(user_categories)} categories")
            for cat in user_categories[:5]:  # Show first 5
                print(f"  - {cat.name} (ID: {cat.id})")
            if len(user_categories) > 5:
                print(f"  ... and {len(user_categories) - 5} more")
        
        print("\n🎉 Development setup complete!")
        print("\nYou can now:")
        print("1. Start the backend server: uvicorn app.main:app --reload --port 8000")
        print("2. Test budget plan creation with any of the categories above")
        print("3. Use the /dev-budget-plans endpoints for testing without authentication")
        
    except Exception as e:
        print(f"❌ Error setting up development data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_dev_data()