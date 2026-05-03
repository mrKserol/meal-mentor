"""Сводка для веб-страницы «Дневник»: недавние приёмы, неделя, сегодня, вес."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

import zoneinfo
from sqlalchemy.orm import Session, joinedload

from app.db.models import Meal, MealItem, User
from app.db.repository import list_user_measurements
from app.schemas.diary import (
    DiaryRecentMeal,
    DiarySnapshotResponse,
    DiaryTodayTotals,
    DiaryWeightCard,
    DiaryWeekBlock,
    DiaryWeekDay,
)

_WEEKDAY_RU = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")

_MEAL_TYPE_RU: dict[str, str] = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
}


def _resolve_tz(user: User) -> zoneinfo.ZoneInfo:
    raw = (user.timezone or "").strip() or "UTC"
    try:
        return zoneinfo.ZoneInfo(raw)
    except Exception:
        return zoneinfo.ZoneInfo("UTC")


def _as_utc_naive(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(timezone.utc).replace(tzinfo=None)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_naive_to_local(dt: datetime, tz: zoneinfo.ZoneInfo) -> datetime:
    utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    return utc.astimezone(tz)


def _week_range_utc_naive(user: User) -> tuple[datetime, datetime, date, zoneinfo.ZoneInfo]:
    tz = _resolve_tz(user)
    now_local = datetime.now(tz)
    d = now_local.date()
    monday = d - timedelta(days=d.weekday())
    next_monday = monday + timedelta(days=7)
    start_local = datetime.combine(monday, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(next_monday, datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc, monday, tz


def _today_range_utc_naive(user: User) -> tuple[datetime, datetime]:
    tz = _resolve_tz(user)
    now_local = datetime.now(tz)
    d = now_local.date()
    tomorrow = d + timedelta(days=1)
    start_local = datetime.combine(d, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def _sum_meal_nutrition(meal: Meal) -> dict[str, int]:
    c = p = f = cb = 0
    for item in meal.items:
        n = item.nutrition
        if n is None:
            continue
        c += n.calories or 0
        p += n.protein_g or 0
        f += n.fat_g or 0
        cb += n.carbs_g or 0
    return {"calories": c, "protein_g": p, "fat_g": f, "carbs_g": cb}


def _meal_naive_dt(meal: Meal) -> datetime:
    dt = meal.meal_datetime
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _meal_title(meal: Meal, max_parts: int = 3) -> str:
    names = [it.item_name for it in meal.items if it.item_name]
    if not names:
        return "Приём пищи"
    head = names[:max_parts]
    tail = "…" if len(names) > max_parts else ""
    return ", ".join(head) + tail


def _meal_type_label(raw: str | None) -> str:
    if not raw:
        return "Приём пищи"
    return _MEAL_TYPE_RU.get(raw.lower(), raw)


def build_diary_snapshot(db: Session, user: User) -> DiarySnapshotResponse:
    start_utc, end_utc, monday, tz = _week_range_utc_naive(user)
    sunday = monday + timedelta(days=6)

    meals_week = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= start_utc, Meal.meal_datetime < end_utc)
        .all()
    )

    by_day_cal: dict[date, int] = defaultdict(int)
    week_p = week_f = week_cb = 0

    for meal in meals_week:
        local = _utc_naive_to_local(_meal_naive_dt(meal), tz)
        d = local.date()
        if d < monday or d > sunday:
            continue
        t = _sum_meal_nutrition(meal)
        by_day_cal[d] += t["calories"]
        week_p += t["protein_g"]
        week_f += t["fat_g"]
        week_cb += t["carbs_g"]

    days_with_data = sum(1 for i in range(7) if by_day_cal.get(monday + timedelta(days=i), 0) > 0)
    div = max(1, days_with_data)

    max_cal = max((by_day_cal.get(monday + timedelta(days=i), 0) for i in range(7)), default=0)
    week_days: list[DiaryWeekDay] = []
    for i in range(7):
        dd = monday + timedelta(days=i)
        cal = by_day_cal.get(dd, 0)
        if max_cal <= 0 or cal <= 0:
            pct = 0
        else:
            pct = min(100, max(8, int(round(100 * cal / max_cal))))
        week_days.append(DiaryWeekDay(date=dd, weekday_short=_WEEKDAY_RU[i], calories=cal, bar_percent=pct))

    week_block = DiaryWeekBlock(
        days=week_days,
        avg_calories=round(sum(by_day_cal.values()) / div, 1),
        avg_protein_g=round(week_p / div, 1),
        avg_fat_g=round(week_f / div, 1),
        avg_carbs_g=round(week_cb / div, 1),
        days_with_data=days_with_data,
    )

    t_start, t_end = _today_range_utc_naive(user)
    meals_today = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= t_start, Meal.meal_datetime < t_end)
        .all()
    )
    tc = tp = tf = tcb = 0
    for meal in meals_today:
        nut = _sum_meal_nutrition(meal)
        tc += nut["calories"]
        tp += nut["protein_g"]
        tf += nut["fat_g"]
        tcb += nut["carbs_g"]
    today = DiaryTodayTotals(calories=tc, protein_g=tp, fat_g=tf, carbs_g=tcb)

    recent_db = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id)
        .order_by(Meal.meal_datetime.desc())
        .limit(3)
        .all()
    )
    recent: list[DiaryRecentMeal] = []
    for meal in recent_db:
        local = _utc_naive_to_local(_meal_naive_dt(meal), tz)
        tot = _sum_meal_nutrition(meal)
        raw_dt = meal.meal_datetime
        recorded = raw_dt.replace(tzinfo=None) if raw_dt.tzinfo else raw_dt
        recent.append(
            DiaryRecentMeal(
                id=meal.id,
                title=_meal_title(meal),
                meal_type=meal.meal_type,
                meal_type_label=_meal_type_label(meal.meal_type),
                time_local=local.strftime("%H:%M"),
                calories=tot["calories"],
                recorded_at=recorded,
            )
        )

    delta_week: float | None = None
    meas = list_user_measurements(db, user.id, limit=100)
    in_week_w: list[Any] = []
    for m in meas:
        if m.weight_kg is None:
            continue
        at = m.measured_at
        at_u = at.replace(tzinfo=None) if at.tzinfo is None else _as_utc_naive(at)
        if start_utc <= at_u < end_utc:
            in_week_w.append(m)
    if len(in_week_w) >= 2:
        asc = sorted(in_week_w, key=lambda x: x.measured_at)
        delta_week = round(float(asc[-1].weight_kg) - float(asc[0].weight_kg), 2)

    weight_card = DiaryWeightCard(
        weight_kg=float(user.weight_kg) if user.weight_kg is not None else None,
        delta_week_kg=delta_week,
    )

    return DiarySnapshotResponse(
        recent_meals=recent,
        week=week_block,
        today=today,
        weight=weight_card,
    )
