"""Сводка для веб-страницы «Дневник»: недавние приёмы, статистика за последние 7 / 30 дней, сегодня, вес."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any

import zoneinfo
from sqlalchemy.orm import Session, joinedload

from app.core.config import BASE_URL
from app.db.models import Meal, MealItem, User
from app.db.nutrition_columns import MEAL_ITEM_NUTRITION_KEYS
from app.services.meal_serialization import meal_composition_line
from app.db.repository import list_user_measurements
from app.schemas.diary import (
    DiaryPeriodBlock,
    DiaryPeriodDay,
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
logger = logging.getLogger(__name__)

_PRIMARY_DAILY_KEYS = frozenset({"calories", "protein_g", "fat_g", "carbs_g", "fiber_g"})


def _init_detailed_sums() -> dict[str, float]:
    return {k: 0.0 for k in MEAL_ITEM_NUTRITION_KEYS if k not in _PRIMARY_DAILY_KEYS}


def _accumulate_detailed_meal_nutrients(meal: Meal, totals: dict[str, float]) -> None:
    for item in meal.items:
        n = item.nutrition
        if n is None:
            continue
        for key in totals.keys():
            totals[key] += float(getattr(n, key, 0.0) or 0.0)


def _warn_suspicious_nutrient_mapping(avg_values: dict[str, float], *, avg_fat_g: float) -> None:
    cholesterol_mg = float(avg_values.get("cholesterol_mg", 0.0) or 0.0)
    trans_mg = float(avg_values.get("fatty_acids_total_trans_mg", 0.0) or 0.0)
    if cholesterol_mg > 0 and trans_mg > 0 and cholesterol_mg == trans_mg:
        logger.warning(
            "Suspicious nutrient mapping: cholesterol_mg equals fatty_acids_total_trans_mg",
            extra={
                "cholesterol_mg": cholesterol_mg,
                "fatty_acids_total_trans_mg": trans_mg,
            },
        )
    trans_fat_g = trans_mg / 1000.0
    if avg_fat_g > 0 and trans_fat_g > avg_fat_g:
        logger.warning(
            "Suspicious nutrient data: trans fat is greater than total fat",
            extra={
                "fat_g": avg_fat_g,
                "fatty_acids_total_trans_mg": trans_mg,
                "trans_fat_g": trans_fat_g,
            },
        )


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


def _rolling_7_days_utc_naive(user: User) -> tuple[datetime, datetime, date, date, zoneinfo.ZoneInfo]:
    """Последние 7 календарных дней включая сегодня (локаль TZ профиля)."""
    tz = _resolve_tz(user)
    today = datetime.now(tz).date()
    first = today - timedelta(days=6)
    tomorrow = today + timedelta(days=1)
    start_local = datetime.combine(first, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc, first, today, tz


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


def _rolling_30_days_utc_naive(user: User) -> tuple[datetime, datetime, date, date, zoneinfo.ZoneInfo]:
    """Последние 30 календарных дней включая сегодня (локаль TZ профиля)."""
    tz = _resolve_tz(user)
    today = datetime.now(tz).date()
    first = today - timedelta(days=29)
    tomorrow = today + timedelta(days=1)
    start_local = datetime.combine(first, datetime.min.time(), tzinfo=tz)
    end_local = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tz)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc, first, today, tz


def _sum_meal_nutrition(meal: Meal) -> dict[str, int | float]:
    c = p = f = cb = 0
    fib = 0.0
    sugar = 0.0
    sodium_mg = 0.0
    sat_fat = 0.0
    water = 0.0
    for item in meal.items:
        n = item.nutrition
        if n is None:
            continue
        c += n.calories or 0
        p += n.protein_g or 0
        f += n.fat_g or 0
        cb += n.carbs_g or 0
        fib += float(n.fiber_g or 0)
        sugar += float(n.sugar_g or 0)
        sodium_mg += float(n.sodium_mg or 0)
        sat_fat += float(n.saturated_fat_g or 0)
        water += float(n.water_g or 0)
    return {
        "calories": c,
        "protein_g": p,
        "fat_g": f,
        "carbs_g": cb,
        "fiber_g": round(fib, 2),
        "sugar_g": round(sugar, 2),
        "sodium_mg": round(sodium_mg, 2),
        "saturated_fat_g": round(sat_fat, 2),
        "water_g": round(water, 2),
    }


def _absolute_public_url(web_path: str | None) -> str | None:
    if not web_path:
        return None
    p = web_path.strip()
    if p.startswith("http://") or p.startswith("https://"):
        return p
    base = BASE_URL.rstrip("/")
    if not p.startswith("/"):
        p = "/" + p
    return f"{base}{p}"


def _meal_naive_dt(meal: Meal) -> datetime:
    dt = meal.meal_datetime
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _meal_title_from_items(meal: Meal, max_parts: int = 3) -> str:
    names = [it.item_name for it in meal.items if it.item_name]
    if not names:
        return "Приём пищи"
    head = names[:max_parts]
    tail = "…" if len(names) > max_parts else ""
    return ", ".join(head) + tail


def _meal_list_title(meal: Meal, max_len: int = 160) -> str:
    """Строка для списка «История»: user_text, иначе prediction, иначе старая сводка из meal_items."""
    ut = (meal.user_text or "").strip()
    if ut:
        return ut if len(ut) <= max_len else ut[: max_len - 1] + "…"
    pr = (meal.prediction or "").strip()
    if pr:
        return pr if len(pr) <= max_len else pr[: max_len - 1] + "…"
    return _meal_title_from_items(meal)


def _meal_type_label(raw: str | None) -> str:
    if not raw:
        return "Приём пищи"
    return _MEAL_TYPE_RU.get(raw.lower(), raw)


def build_diary_snapshot(db: Session, user: User) -> DiarySnapshotResponse:
    week_start_utc, week_end_utc, week_first, week_last, tz = _rolling_7_days_utc_naive(user)

    meals_week = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= week_start_utc, Meal.meal_datetime < week_end_utc)
        .all()
    )

    by_day_cal: dict[date, int] = defaultdict(int)
    week_p = week_f = week_cb = 0
    week_fiber = 0.0
    week_details = _init_detailed_sums()

    for meal in meals_week:
        local = _utc_naive_to_local(_meal_naive_dt(meal), tz)
        d = local.date()
        if d < week_first or d > week_last:
            continue
        t = _sum_meal_nutrition(meal)
        by_day_cal[d] += t["calories"]
        week_p += t["protein_g"]
        week_f += t["fat_g"]
        week_cb += t["carbs_g"]
        week_fiber += float(t["fiber_g"])
        _accumulate_detailed_meal_nutrients(meal, week_details)

    days_with_data = sum(1 for i in range(7) if by_day_cal.get(week_first + timedelta(days=i), 0) > 0)
    div = max(1, days_with_data)

    max_cal = max((by_day_cal.get(week_first + timedelta(days=i), 0) for i in range(7)), default=0)
    week_days: list[DiaryWeekDay] = []
    for i in range(7):
        dd = week_first + timedelta(days=i)
        cal = by_day_cal.get(dd, 0)
        if max_cal <= 0 or cal <= 0:
            pct = 0
        else:
            pct = min(100, max(8, int(round(100 * cal / max_cal))))
        day_label = _WEEKDAY_RU[dd.weekday()]
        week_days.append(DiaryWeekDay(date=dd, weekday_short=day_label, calories=cal, bar_percent=pct))

    week_detailed_avg = {k: round(v / div, 3) for k, v in week_details.items()}
    _warn_suspicious_nutrient_mapping(week_detailed_avg, avg_fat_g=round(week_f / div, 1))
    week_block = DiaryWeekBlock(
        days=week_days,
        avg_calories=round(sum(by_day_cal.values()) / div, 1),
        avg_protein_g=round(week_p / div, 1),
        avg_fat_g=round(week_f / div, 1),
        avg_carbs_g=round(week_cb / div, 1),
        avg_fiber_g=round(week_fiber / div, 1),
        avg_sugar_g=round(week_detailed_avg.get("sugar_g", 0.0), 1),
        avg_salt_g=round((week_detailed_avg.get("sodium_mg", 0.0) * 2.54 / 1000.0), 2),
        avg_saturated_fat_g=round(week_detailed_avg.get("saturated_fat_g", 0.0), 1),
        detailed_avg=week_detailed_avg,
        days_with_data=days_with_data,
    )

    m_start_utc, m_end_utc, month_first, month_last, tz_m = _rolling_30_days_utc_naive(user)
    meals_month = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= m_start_utc, Meal.meal_datetime < m_end_utc)
        .all()
    )
    month_by_cal: dict[date, int] = defaultdict(int)
    month_p = month_f = month_cb = 0
    month_fiber = 0.0
    month_details = _init_detailed_sums()
    for meal in meals_month:
        local = _utc_naive_to_local(_meal_naive_dt(meal), tz_m)
        d = local.date()
        if d < month_first or d > month_last:
            continue
        t = _sum_meal_nutrition(meal)
        month_by_cal[d] += t["calories"]
        month_p += t["protein_g"]
        month_f += t["fat_g"]
        month_cb += t["carbs_g"]
        month_fiber += float(t["fiber_g"])
        _accumulate_detailed_meal_nutrients(meal, month_details)

    month_span = 30
    month_days_with = sum(
        1 for i in range(month_span) if month_by_cal.get(month_first + timedelta(days=i), 0) > 0
    )
    month_div = max(1, month_days_with)
    month_max_cal = max(
        (month_by_cal.get(month_first + timedelta(days=i), 0) for i in range(month_span)),
        default=0,
    )
    period_days: list[DiaryPeriodDay] = []
    for i in range(month_span):
        dd = month_first + timedelta(days=i)
        cal = month_by_cal.get(dd, 0)
        if month_max_cal <= 0 or cal <= 0:
            pct = 0
        else:
            pct = min(100, max(8, int(round(100 * cal / month_max_cal))))
        period_days.append(
            DiaryPeriodDay(date=dd, label=f"{dd.day}.{dd.month}", calories=cal, bar_percent=pct),
        )
    month_detailed_avg = {k: round(v / month_div, 3) for k, v in month_details.items()}
    _warn_suspicious_nutrient_mapping(month_detailed_avg, avg_fat_g=round(month_f / month_div, 1))
    month_block = DiaryPeriodBlock(
        days=period_days,
        avg_calories=round(sum(month_by_cal.values()) / month_div, 1),
        avg_protein_g=round(month_p / month_div, 1),
        avg_fat_g=round(month_f / month_div, 1),
        avg_carbs_g=round(month_cb / month_div, 1),
        avg_fiber_g=round(month_fiber / month_div, 1),
        avg_sugar_g=round(month_detailed_avg.get("sugar_g", 0.0), 1),
        avg_salt_g=round((month_detailed_avg.get("sodium_mg", 0.0) * 2.54 / 1000.0), 2),
        avg_saturated_fat_g=round(month_detailed_avg.get("saturated_fat_g", 0.0), 1),
        detailed_avg=month_detailed_avg,
        days_with_data=month_days_with,
    )

    t_start, t_end = _today_range_utc_naive(user)
    meals_today = (
        db.query(Meal)
        .options(joinedload(Meal.items).joinedload(MealItem.nutrition))
        .filter(Meal.user_id == user.id, Meal.meal_datetime >= t_start, Meal.meal_datetime < t_end)
        .all()
    )
    tc = tp = tf = tcb = 0
    tfib = 0.0
    for meal in meals_today:
        nut = _sum_meal_nutrition(meal)
        tc += nut["calories"]
        tp += nut["protein_g"]
        tf += nut["fat_g"]
        tcb += nut["carbs_g"]
        tfib += float(nut["fiber_g"])
    today = DiaryTodayTotals(calories=tc, protein_g=tp, fat_g=tf, carbs_g=tcb, fiber_g=round(tfib, 2))

    meals_today_desc = sorted(meals_today, key=lambda m: m.meal_datetime, reverse=True)
    today_meals: list[DiaryRecentMeal] = []
    for meal in meals_today_desc:
        local = _utc_naive_to_local(_meal_naive_dt(meal), tz)
        tot = _sum_meal_nutrition(meal)
        raw_dt = meal.meal_datetime
        recorded = raw_dt.replace(tzinfo=None) if raw_dt.tzinfo else raw_dt
        today_meals.append(
            DiaryRecentMeal(
                id=meal.id,
                title=_meal_list_title(meal),
                meal_type=meal.meal_type,
                meal_type_label=_meal_type_label(meal.meal_type),
                time_local=local.strftime("%H:%M"),
                calories=tot["calories"],
                protein_g=tot["protein_g"],
                fat_g=tot["fat_g"],
                carbs_g=tot["carbs_g"],
                fiber_g=tot["fiber_g"],
                sugar_g=tot["sugar_g"],
                sodium_mg=tot["sodium_mg"],
                saturated_fat_g=tot["saturated_fat_g"],
                water_g=tot["water_g"],
                recorded_at=recorded,
                prediction=meal.prediction,
                user_text=meal.user_text,
                composition=meal_composition_line(meal),
                meal_photo_large=meal.meal_photo_large,
                meal_photo_thumb=meal.meal_photo_thumb,
                meal_photo_large_url=_absolute_public_url(meal.meal_photo_large),
                meal_photo_thumb_url=_absolute_public_url(meal.meal_photo_thumb),
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
        if week_start_utc <= at_u < week_end_utc:
            in_week_w.append(m)
    if len(in_week_w) >= 2:
        asc = sorted(in_week_w, key=lambda x: x.measured_at)
        delta_week = round(float(asc[-1].weight_kg) - float(asc[0].weight_kg), 2)

    weight_card = DiaryWeightCard(
        weight_kg=float(user.weight_kg) if user.weight_kg is not None else None,
        delta_week_kg=delta_week,
    )

    return DiarySnapshotResponse(
        today_meals=today_meals,
        week=week_block,
        month=month_block,
        today=today,
        weight=weight_card,
    )
