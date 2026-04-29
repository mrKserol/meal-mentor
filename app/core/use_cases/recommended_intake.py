"""
Daily calorie target (ТЗ formulas) + BJU heuristic (20% / 30% / 50%).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.db.models import User


def _activity_multiplier(activity_level: str | None) -> float:
    if not activity_level:
        return 1.0
    s = str(activity_level).strip().lower()
    if s in ("1", "1.0", "low", "низкая"):
        return 1.0
    if s in ("1.3", "medium", "средняя"):
        return 1.3
    if s in ("1.5", "high", "высокая"):
        return 1.5
    try:
        v = float(s.replace(",", "."))
        if abs(v - 1.0) < 0.01:
            return 1.0
        if abs(v - 1.3) < 0.01:
            return 1.3
        if abs(v - 1.5) < 0.01:
            return 1.5
    except ValueError:
        pass
    return 1.0


def _age_years(birth: date, today: date | None = None) -> int | None:
    if birth is None:
        return None
    t = today or date.today()
    return t.year - birth.year - ((t.month, t.day) < (birth.month, birth.day))


def _bmr_formula(sex: str | None, age: int, weight_kg: float) -> float | None:
    """Returns base component before *240*KFA (per ТЗ)."""
    if sex is None or age is None:
        return None
    s = str(sex).strip().lower()
    w = weight_kg
    if s in ("f", "female", "ж", "женский", "woman"):
        if 18 <= age <= 30:
            return (0.062 * w + 2.036) * 240
        if 31 <= age <= 60:
            return (0.034 * w + 3.538) * 240
        if age > 60:
            return (0.038 * w + 2.755) * 240
        return None
    if s in ("m", "male", "м", "мужской", "man"):
        if 18 <= age <= 30:
            return (0.063 * w + 2.896) * 240
        if 31 <= age <= 60:
            return (0.048 * w + 3.653) * 240
        if age > 60:
            return (0.049 * w + 2.459) * 240
        return None
    return None


def compute_recommended_intake(user: User, *, today: date | None = None) -> dict[str, Any]:
    """
    Returns calories_kcal, protein_g, fat_g, carbs_g, meta (reason if incomplete).
    """
    missing = []
    if user.weight_kg is None:
        missing.append("weight_kg")
    if user.birth_date is None:
        missing.append("birth_date")
    if not user.sex:
        missing.append("sex")
    if missing:
        return {
            "status": "incomplete",
            "missing_fields": missing,
            "message": "Заполните пол, дату рождения и вес для расчёта нормы.",
        }
    age = _age_years(user.birth_date, today)
    if age is None or age < 18:
        return {
            "status": "error",
            "message": "Расчёт предусмотрен для возраста 18+ лет.",
        }
    kfa = _activity_multiplier(user.activity_level)
    base = _bmr_formula(user.sex, age, float(user.weight_kg))
    if base is None:
        return {"status": "error", "message": "Не удалось определить пол для формулы."}
    calories = base * kfa
    cal = float(calories)
    protein_g = (0.20 * cal) / 4.0
    fat_g = (0.30 * cal) / 9.0
    carbs_g = (0.50 * cal) / 4.0
    return {
        "status": "ok",
        "calories_kcal": round(cal, 0),
        "protein_g": round(protein_g, 1),
        "fat_g": round(fat_g, 1),
        "carbs_g": round(carbs_g, 1),
        "activity_multiplier": kfa,
        "age_years": age,
    }
