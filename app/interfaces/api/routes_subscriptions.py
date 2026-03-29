from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import SUBSCRIPTION_DEMO_AUTO
from app.db.session import get_db
from app.db.repository import (
    activate_subscription_for_demo,
    create_subscription_stub,
    get_active_subscription,
    get_user_by_telegram_id,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

PLAN_DAYS = {
    "tariff_1w": 7,
    "tariff_2w": 14,
    "tariff_1m": 30,
}


class OrderBody(BaseModel):
    telegram_id: int
    plan: str


@router.get("/status")
def subscription_status(telegram_id: int = Query(...), db: Session = Depends(get_db)):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"active": False, "subscription": None}
    sub = get_active_subscription(db, user.id)
    if not sub:
        return {"active": False, "subscription": None}
    return {
        "active": True,
        "subscription": {
            "id": sub.id,
            "plan": sub.plan,
            "status": sub.status,
            "provider": sub.provider,
            "payment_status": sub.payment_status,
            "started_at": sub.started_at.isoformat() if sub.started_at else None,
            "ends_at": sub.ends_at.isoformat() if sub.ends_at else None,
        },
    }


@router.post("/order")
def create_order(body: OrderBody, db: Session = Depends(get_db)):
    if body.plan not in PLAN_DAYS:
        raise HTTPException(400, "unknown plan")
    user = get_user_by_telegram_id(db, body.telegram_id)
    if not user:
        raise HTTPException(404, "user not found")
    row = create_subscription_stub(db, user.id, body.plan)
    if SUBSCRIPTION_DEMO_AUTO:
        days = PLAN_DAYS[body.plan]
        activate_subscription_for_demo(db, row.id, days=days)
        db.refresh(row)
    return {
        "status": "pending" if not SUBSCRIPTION_DEMO_AUTO else "active",
        "subscription_id": row.id,
        "plan": row.plan,
        "message": "Оплата Robokassa будет подключена позже."
        if not SUBSCRIPTION_DEMO_AUTO
        else "Демо-активация (SUBSCRIPTION_DEMO_AUTO).",
    }
