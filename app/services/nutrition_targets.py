"""Calculate and persist daily nutrition targets (Mifflin–St Jeor + macro split)."""

from __future__ import annotations

import math
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.auth.profile import is_profile_completed
from app.db.models import NutritionTarget, User


def calculate_age(birth_date: date) -> int:
    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return max(age, 0)


def calculate_bmr_mifflin_st_jeor(
    sex: str | None,
    birth_date: date,
    height_cm: int,
    weight_kg: float,
) -> int:
    age = calculate_age(birth_date)
    s = str(sex).strip().lower() if sex else ""
    is_female = s in {"female", "f", "ж", "жен", "женский"}
    core = 10 * weight_kg + 6.25 * height_cm - 5 * age
    bmr = core - 161 if is_female else core + 5
    return int(round(bmr))


# Standard TDEE multipliers (stored as decimal strings on the user profile).
_MULTIPLIERS: tuple[float, ...] = (
    1.9,
    1.725,
    1.55,
    1.375,
    1.2,
    # Legacy web / telegram values (backward compatible)
    1.5,
    1.3,
    1.0,
)

_LEGACY_ACTIVITY_TERMS: dict[str, float] = {
    "low": 1.0,
    "moderate": 1.3,
    "high": 1.5,
    "низкая": 1.0,
    "средняя": 1.3,
    "высокая": 1.5,
}


def activity_multiplier_for_level(activity_level: str | None) -> float:
    """PAL / activity factor for TDEE. Unknown → 1.0 (conservative fallback)."""
    if activity_level is None:
        return 1.0
    raw = str(activity_level).strip()
    if not raw:
        return 1.0
    lowered = raw.lower()
    if lowered in _LEGACY_ACTIVITY_TERMS:
        return _LEGACY_ACTIVITY_TERMS[lowered]
    try:
        v = float(lowered.replace(",", "."))
    except ValueError:
        return 1.0
    for m in _MULTIPLIERS:
        if math.isclose(v, m, rel_tol=0.0, abs_tol=1e-3):
            return float(m)
    return 1.0


def calculate_tdee(bmr_kcal: int, activity_level: str) -> int:
    mult = activity_multiplier_for_level(activity_level)
    return int(round(bmr_kcal * mult))


def calculate_target_calories(tdee_kcal: int, goal: str | None) -> int:
    g = (goal or "").strip().lower()
    if g == "lose_weight":
        return int(round(tdee_kcal * 0.85))
    if g == "gain_weight":
        return int(round(tdee_kcal * 1.10))
    return int(round(tdee_kcal))


def calculate_macros(target_calories: int, weight_kg: float, goal: str | None) -> dict[str, int]:
    g = (goal or "").strip().lower()
    if g == "lose_weight":
        protein_per_kg = 2.0
    elif g == "gain_weight":
        protein_per_kg = 1.8
    else:
        protein_per_kg = 1.6

    fat_per_kg = 0.9

    protein_g = int(round(protein_per_kg * weight_kg))
    fat_g = int(round(fat_per_kg * weight_kg))

    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    remaining = target_calories - protein_kcal - fat_kcal
    carbs_g = int(round(max(remaining, 0) / 4))
    return {"protein_g": protein_g, "fat_g": fat_g, "carbs_g": carbs_g}


def get_active_nutrition_target(db: Session, *, user_id: int) -> NutritionTarget | None:
    return (
        db.query(NutritionTarget)
        .filter(NutritionTarget.user_id == user_id, NutritionTarget.is_active.is_(True))
        .first()
    )


def _target_matches(
    row: NutritionTarget,
    *,
    bmr_kcal: int,
    tdee_kcal: int,
    target_calories: int,
    macros: dict[str, int],
    user: User,
) -> bool:
    return (
        row.bmr_kcal == bmr_kcal
        and row.tdee_kcal == tdee_kcal
        and row.target_calories == target_calories
        and row.target_protein_g == macros["protein_g"]
        and row.target_fat_g == macros["fat_g"]
        and row.target_carbs_g == macros["carbs_g"]
        and row.goal == user.goal
        and row.activity_level == user.activity_level
        and row.weight_kg == user.weight_kg
        and row.target_weight_kg == user.target_weight_kg
    )


def create_or_update_active_nutrition_target(
    db: Session,
    user: User,
    *,
    force_new: bool = False,
) -> NutritionTarget | None:
    if not is_profile_completed(user):
        return None

    if not user.sex or not user.birth_date or user.height_cm is None:
        return None
    if user.weight_kg is None or not user.goal or not user.activity_level:
        return None
    if user.target_weight_kg is None:
        return None

    height_cm = int(user.height_cm)
    weight_kg = float(user.weight_kg)

    bmr = calculate_bmr_mifflin_st_jeor(
        user.sex,
        user.birth_date,
        height_cm=height_cm,
        weight_kg=weight_kg,
    )
    tdee = calculate_tdee(bmr, user.activity_level)
    target_cal = calculate_target_calories(tdee, user.goal)
    macros = calculate_macros(target_cal, weight_kg, user.goal)

    now = datetime.utcnow()
    existing = get_active_nutrition_target(db, user_id=user.id)

    if existing is not None:
        if _target_matches(
            existing,
            bmr_kcal=bmr,
            tdee_kcal=tdee,
            target_calories=target_cal,
            macros=macros,
            user=user,
        ) and not force_new:
            return existing
        existing.is_active = False
        existing.updated_at = now
        db.add(existing)

    row = NutritionTarget(user_id=user.id)

    row.bmr_kcal = bmr
    row.tdee_kcal = tdee
    row.target_calories = target_cal
    row.target_protein_g = macros["protein_g"]
    row.target_fat_g = macros["fat_g"]
    row.target_carbs_g = macros["carbs_g"]
    row.formula_name = "mifflin_st_jeor"
    row.goal = user.goal
    row.activity_level = user.activity_level
    row.weight_kg = user.weight_kg
    row.target_weight_kg = user.target_weight_kg
    row.is_active = True
    row.created_at = now
    row.updated_at = now

    db.add(row)
    return row
