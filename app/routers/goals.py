from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/goals", tags=["goals"])

@router.get("", response_model=List[schemas.GoalResponse])
def get_goals(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get all goals for the current user"""
    goals = db.query(models.Goal).filter_by(user_id=current_user.id).all()
    return goals

@router.get("/{goal_id}", response_model=schemas.GoalResponse)
def get_goal(goal_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Get a specific goal by ID"""
    goal = db.query(models.Goal).filter_by(id=goal_id, user_id=current_user.id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@router.post("", response_model=schemas.GoalResponse)
def create_goal(goal: schemas.GoalCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_goal = models.Goal(
        user_id=current_user.id,
        name=goal.name,
        description=goal.description,
        target_amount=goal.target_amount,
        deadline=goal.deadline
    )
    db.add(db_goal)
    db.flush()  # Get db_goal.id

    if goal.create_temporary_category:
        temp_category = models.Category(
            name=goal.temporary_category_name or f"{goal.name} Savings",
            user_id=current_user.id,
            is_temporary=True,
            linked_goal_id=db_goal.id
        )
        db.add(temp_category)
        db.flush()
        db_goal.linked_category_id = temp_category.id

    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.put("/{goal_id}", response_model=schemas.GoalResponse)
def update_goal(goal_id: str, goal: schemas.GoalUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_goal = db.query(models.Goal).filter_by(id=goal_id, user_id=current_user.id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in goal.dict(exclude_unset=True).items():
        setattr(db_goal, field, value)
    db.commit()
    db.refresh(db_goal)
    return db_goal

@router.delete("/{goal_id}")
def delete_goal(goal_id: str, action: str = Query(None, description="Action to take if goal has linked transactions: archive, complete, abandon"), delete_temp_category: bool = False, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_goal = db.query(models.Goal).filter_by(id=goal_id, user_id=current_user.id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    # Check for transactions linked to the goal's category
    if db_goal.linked_category_id:
        tx_count = db.query(models.Transaction).filter(
            models.Transaction.category_id == db_goal.linked_category_id,
            models.Transaction.is_deleted == False
        ).count()
        if tx_count > 0:
            # Take action if transactions exist
            valid_actions = {"archive", "complete", "abandon"}
            chosen_action = action if action in valid_actions else "archive"
            db_goal.status = chosen_action
            db.commit()
            return {"detail": f"Goal status set to '{chosen_action}' because it has linked transactions. Cannot delete."}
    # Optionally delete linked temporary category
    if delete_temp_category and db_goal.linked_category_id:
        temp_cat = db.query(models.Category).filter_by(id=db_goal.linked_category_id, is_temporary=True).first()
        if temp_cat:
            db.delete(temp_cat)
    db.delete(db_goal)
    db.commit()
    return {"detail": "Goal deleted"}

@router.put("/{goal_id}/status", response_model=schemas.GoalResponse)
def update_goal_status(goal_id: str, status: str = Query(..., description="New status: archive, complete, abandon, active"), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    db_goal = db.query(models.Goal).filter_by(id=goal_id, user_id=current_user.id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    valid_statuses = {"archive", "complete", "abandon", "active"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status value")
    db_goal.status = status
    db.commit()
    db.refresh(db_goal)
    return db_goal 