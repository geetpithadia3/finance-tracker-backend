"""
Reports Router (V2)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.core import dependencies
from app import auth
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
    responses={404: {"description": "Not found"}},
)

def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    return ReportService(db)

@router.get("/monthly-category")
def get_monthly_category_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(auth.get_current_user),
    service: ReportService = Depends(get_report_service)
):
    """
    Get total expenses per category for a specific month.
    """
    return service.get_expenses_by_category(current_user, year, month)

@router.get("/monthly-summary")
def get_monthly_summary_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(auth.get_current_user),
    service: ReportService = Depends(get_report_service)
):
    """
    Get High-level Income vs Expense summary.
    """
    return service.get_monthly_summary(current_user, year, month)
