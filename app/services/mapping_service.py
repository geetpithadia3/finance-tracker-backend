"""
Mapping Service (V2)
Handles Auto-Categorization Rules
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models import MappingRule
import logging

logger = logging.getLogger(__name__)

class MappingService:
    def __init__(self, db: Session):
        self.db = db

    def create_rule(self, owner_id: str, match_pattern: str, target_category_id: str, priority: int = 0) -> MappingRule:
        """Create a new mapping rule"""
        rule = MappingRule(
            owner_id=owner_id,
            match_pattern=match_pattern,
            target_category_id=target_category_id,
            priority=priority
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rules(self, owner_id: str) -> List[MappingRule]:
        return self.db.query(MappingRule).filter(
            MappingRule.owner_id == owner_id
        ).order_by(desc(MappingRule.priority)).all()

    def delete_rule(self, rule_id: str, owner_id: str):
        rule = self.db.query(MappingRule).filter(
            MappingRule.id == rule_id,
            MappingRule.owner_id == owner_id
        ).first()
        if rule:
            self.db.delete(rule)
            self.db.commit()

    def apply_rules(self, owner_id: str, description: str) -> Optional[str]:
        """
        Returns the target_category_id if a match is found, else None.
        """
        rules = self.get_rules(owner_id)
        
        # Apply rules in priority order (desc)
        for rule in rules:
            # Case-insensitive partial match
            if rule.match_pattern.lower() in description.lower():
                return rule.target_category_id
        return None
