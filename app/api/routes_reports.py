from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.repository import get_user_by_telegram_id
from app.services.report_service import get_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def report_summary(
    telegram_id: int = Query(..., description="Telegram user id"),
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Aggregated nutrition for the last `days` days for the user."""
    return get_report(db, telegram_id=telegram_id, days=days)
