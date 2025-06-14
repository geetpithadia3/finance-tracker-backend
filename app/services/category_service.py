from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from app import models

logger = logging.getLogger(__name__)


class CategorySeedingService:
    """Service for seeding default categories for new users"""
    
    # Categories that should not be editable by users
    NON_EDITABLE_CATEGORIES = {
        "Income", "Savings", "Transfer", "Credit Card Payment"
    }
    
    # Default categories that provide a good starting point for personal finance tracking
    DEFAULT_CATEGORIES = [
        # Essential Expenses
        {"name": "Housing", "description": "Rent, mortgage, property taxes, home insurance"},
        {"name": "Utilities", "description": "Electricity, gas, water, internet, phone"},
        {"name": "Groceries", "description": "Food shopping, household supplies"},
        {"name": "Transportation", "description": "Gas, car payments, public transit, maintenance"},
        {"name": "Insurance", "description": "Health, auto, life insurance premiums"},
        # General catch-all
        {"name": "General", "description": "General or uncategorized expenses"},
        
        # Lifestyle & Discretionary
        {"name": "Dining Out", "description": "Restaurants, takeout, coffee shops"},
        {"name": "Entertainment", "description": "Movies, streaming, events, hobbies"},
        {"name": "Shopping", "description": "Clothing, personal items, non-essential purchases"},
        {"name": "Health & Fitness", "description": "Gym, medical, pharmacy, wellness"},
        {"name": "Travel", "description": "Vacations, trips, accommodation"},
        
        # Financial & Investment (some non-editable)
        {"name": "Savings", "description": "Emergency fund, general savings"},
        {"name": "Investments", "description": "Stocks, bonds, retirement contributions"},
        {"name": "Debt Payments", "description": "Credit cards, loans, student loans"},
        {"name": "Credit Card Payment", "description": "Credit card payments and transfers"},
        {"name": "Transfer", "description": "Money transfers between accounts"},
        
        # Personal Development
        {"name": "Education", "description": "Courses, books, training, subscriptions"},
        {"name": "Gifts & Donations", "description": "Presents, charity, religious donations"},
        
        # Income Categories (non-editable)
        {"name": "Income", "description": "All income sources"},
    ]
    
    @staticmethod
    def seed_default_categories(db: Session, user_id: str) -> List[models.Category]:
        """
        Create default categories for a new user
        
        Args:
            db: Database session
            user_id: ID of the user to create categories for
            
        Returns:
            List of created category objects
        """
        created_categories = []
        
        try:
            # Check if user already has categories
            existing_count = db.query(models.Category).filter(
                models.Category.user_id == user_id
            ).count()
            
            if existing_count > 0:
                logger.info(f"User {user_id} already has {existing_count} categories, skipping seeding")
                return []
            
            # Create default categories
            for category_data in CategorySeedingService.DEFAULT_CATEGORIES:
                is_editable = category_data["name"] not in CategorySeedingService.NON_EDITABLE_CATEGORIES
                db_category = models.Category(
                    name=category_data["name"],
                    user_id=user_id,
                    is_editable=is_editable,
                    is_active=True
                )
                db.add(db_category)
                created_categories.append(db_category)
            
            db.commit()
            
            # Refresh all categories to get IDs
            for category in created_categories:
                db.refresh(category)
            
            logger.info(f"Successfully created {len(created_categories)} default categories for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error seeding categories for user {user_id}: {e}")
            db.rollback()
            raise
        
        return created_categories
    
    @staticmethod
    def get_default_categories_info() -> List[Dict[str, str]]:
        """
        Get information about default categories without creating them
        
        Returns:
            List of category information dictionaries
        """
        return CategorySeedingService.DEFAULT_CATEGORIES.copy()
    
    @staticmethod
    def seed_custom_categories(db: Session, user_id: str, categories: List[str]) -> List[models.Category]:
        """
        Create custom categories for a user
        
        Args:
            db: Database session
            user_id: ID of the user to create categories for
            categories: List of category names to create
            
        Returns:
            List of created category objects
        """
        created_categories = []
        
        try:
            for category_name in categories:
                # Check if category already exists for this user
                existing = db.query(models.Category).filter(
                    models.Category.user_id == user_id,
                    models.Category.name == category_name
                ).first()
                
                if not existing:
                    is_editable = category_name not in CategorySeedingService.NON_EDITABLE_CATEGORIES
                    db_category = models.Category(
                        name=category_name,
                        user_id=user_id,
                        is_editable=is_editable,
                        is_active=True
                    )
                    db.add(db_category)
                    created_categories.append(db_category)
                else:
                    logger.info(f"Category '{category_name}' already exists for user {user_id}")
            
            if created_categories:
                db.commit()
                
                # Refresh all categories to get IDs
                for category in created_categories:
                    db.refresh(category)
                
                logger.info(f"Successfully created {len(created_categories)} custom categories for user {user_id}")
        
        except Exception as e:
            logger.error(f"Error creating custom categories for user {user_id}: {e}")
            db.rollback()
            raise
        
        return created_categories