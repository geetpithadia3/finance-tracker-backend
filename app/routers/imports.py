"""
Import Router (V2)
Handles CSV uploads
"""
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.core import dependencies
from app import auth
from app.services.import_service import ImportService

router = APIRouter(
    prefix="/imports",
    tags=["Imports"],
    responses={404: {"description": "Not found"}},
)

def get_import_service(db: Session = Depends(get_db)) -> ImportService:
    return ImportService(db)

@router.post("/csv")
async def import_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(auth.get_current_user),
    service: ImportService = Depends(get_import_service)
):
    """
    Import transactions from a CSV file.
    Expected Columns: Date, Description, Amount, Category (optional)
    """
    content = await file.read()
    result = service.import_transactions_csv(content, current_user)
    return result
