from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.use_cases.nutrient_period import aggregate_meals_total
from app.core.use_cases.recommended_intake import compute_recommended_intake
from app.db.session import get_db
from app.db.repository import get_user_by_telegram_id
from app.infrastructure.charts.matplotlib_charts import macros_bar_chart_png

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/recommended")
def recommended_intake(telegram_id: int = Query(...), db: Session = Depends(get_db)):
    user = get_user_by_telegram_id(db, telegram_id)
    if not user:
        return {"status": "error", "message": "user not found"}
    return compute_recommended_intake(user)


@router.get("/stats/chart")
def nutrition_stats_chart(
    telegram_id: int = Query(...),
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
):
    agg = aggregate_meals_total(db, telegram_id, days=days)
    t = agg.get("totals") or {}
    png = macros_bar_chart_png(
        {
            "calories": t.get("calories", 0),
            "protein_g": t.get("protein_g", 0),
            "fat_g": t.get("fat_g", 0),
            "carbs_g": t.get("carbs_g", 0),
        },
        title=f"Нутриенты за {days} дн.",
    )
    return Response(content=png, media_type="image/png")
