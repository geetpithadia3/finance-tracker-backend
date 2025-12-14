"""
Base repository class with common CRUD operations
"""
from typing import Type, TypeVar, Generic, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database import Base
from app.core.exceptions import raise_not_found, DatabaseError
import logging

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common database operations"""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get_by_id(self, id: str) -> Optional[ModelType]:
        """Get a single record by ID"""
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by ID {id}: {e}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__}")

    def get_by_id_or_raise(self, id: str) -> ModelType:
        """Get a single record by ID or raise NotFound exception"""
        obj = self.get_by_id(id)
        if not obj:
            raise_not_found(self.model.__name__, id)
        return obj

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        try:
            return self.db.query(self.model).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__} records")

    def get_by_filters(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get records by filters"""
        try:
            query = self.db.query(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by filters {filters}: {e}")
            raise DatabaseError(f"Failed to retrieve {self.model.__name__} records")

    def create(self, obj_data: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        try:
            db_obj = self.model(**obj_data)
            self.db.add(db_obj)
            self.db.flush()
            self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            logger.error(f"Error creating {self.model.__name__}: {e}")
            self.db.rollback()
            raise DatabaseError(f"Failed to create {self.model.__name__}")

    def update(self, id: str, update_data: Dict[str, Any]) -> ModelType:
        """Update an existing record"""
        try:
            db_obj = self.get_by_id_or_raise(id)
            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            self.db.flush()
            self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            logger.error(f"Error updating {self.model.__name__} {id}: {e}")
            self.db.rollback()
            raise DatabaseError(f"Failed to update {self.model.__name__}")

    def delete(self, id: str) -> bool:
        """Delete a record (hard delete)"""
        try:
            db_obj = self.get_by_id_or_raise(id)
            self.db.delete(db_obj)
            self.db.flush()
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.model.__name__} {id}: {e}")
            self.db.rollback()
            raise DatabaseError(f"Failed to delete {self.model.__name__}")

    def soft_delete(self, id: str) -> ModelType:
        """Soft delete a record (set is_deleted=True)"""
        if hasattr(self.model, 'is_deleted'):
            return self.update(id, {"is_deleted": True})
        else:
            return self.delete(id)

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters"""
        try:
            query = self.db.query(self.model)
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)
            return query.count()
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to count {self.model.__name__} records")

    def exists(self, filters: Dict[str, Any]) -> bool:
        """Check if a record exists with given filters"""
        try:
            query = self.db.query(self.model)
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to check {self.model.__name__} existence")

    def commit(self):
        """Commit the current transaction"""
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            self.db.rollback()
            raise DatabaseError("Failed to commit transaction")

    def rollback(self):
        """Rollback the current transaction"""
        self.db.rollback()