"""
Telegram copy & layout helpers (UI layer only, no business rules).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _age_from_birth(birth_iso: str | None, today: date | None = None) -> str | None:
    if not birth_iso:
        return None
    try:
        parts = birth_iso.split("-")
        if len(parts) != 3:
            return None
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        bd = date(y, m, d)
    except (ValueError, TypeError):
        return None
    t = today or date.today()
    years = t.year - bd.year - ((t.month, t.day) < (bd.month, bd.day))
    if years < 0:
        return None
    return str(years)


def format_profile_card(
    *,
    username: str | None,
    first_name: str | None,
    sex: str | None,
    birth_date: str | None,
    height_cm: int | None,
    weight_kg: float | None,
) -> str:
    un = f"@{username}" if username else "не указан"
    sex_ru = {"male": "мужской", "female": "женский"}.get((sex or "").lower(), sex or "не указан")
    age = _age_from_birth(birth_date)
    age_s = f"{age} лет" if age is not None else "не указан"
    h = f"{height_cm} см" if height_cm is not None else "не указан"
    w = f"{weight_kg:g} кг" if weight_kg is not None else "не указан"
    return (
        f"Пользователь: @{un}\n"
        f"Пол: {sex_ru}\n"
        f"Возраст: {age_s}\n"
        f"Рост: {h}\n"
        f"Текущий вес: {w}"
    )


def format_diary_intro() -> str:
    return (
        "Здесь находится твой дневник питания.\n"
        "Добавляй приёмы пищи по фото или описанию, смотри сводку по нутриентам.\n"
        "Корректируй актуальный вес тела."
    )


def format_weight_monitoring_intro() -> str:
    return (
        "Контрольное взвешивание проводить минимум раз в неделю. "
        "Например: в понедельник сразу после пробуждения, завершив все утренние гигиенические процедуры, "
        "но до первого стакана воды или завтрака."
    )


def format_weight_correction_intro() -> str:
    return (
        "Для чистоты показателей взвешивайтесь утром натощак, после опорожнения кишечника и мочевого пузыря. "
        "Это позволит исключить погрешность, связанную с естественными процессами пищеварения.\n\n"
        "Введите контрольный вес в кг (число)."
    )


def format_recognition_question(ingredients: dict[str, Any]) -> str:
    """Short human-readable line before detailed macros."""
    if not ingredients:
        return "Я не смог выделить ингредиенты. Опиши блюдо текстом или попробуй другое фото."
    parts = []
    for name, w in ingredients.items():
        parts.append(f"{name} ({w} г)")
    if len(parts) == 1:
        tail = parts[0]
    elif len(parts) == 2:
        tail = f"{parts[0]} и {parts[1]}"
    else:
        tail = ", ".join(parts[:-1]) + f" и {parts[-1]}"
    return f"Это похоже на: {tail}.\n\nЯ верно определил?"


def format_meal_analyzed_detail(ingredients: dict[str, Any], nutrition: dict[str, Any] | None) -> str:
    """Full block: list + BJU + save prompt."""
    lines: list[str] = ["Состав и вес (г):"]
    if ingredients:
        for name, weight in ingredients.items():
            lines.append(f"• {name}: {weight} г")
    else:
        lines.append("—")
    if nutrition:
        lines.append("")
        lines.append("БЖУ (оценка):")
        lines.append(
            f"Калории: {nutrition.get('calories', 0)} ккал | "
            f"Б: {nutrition.get('proteins', 0)} г | "
            f"Ж: {nutrition.get('fats', 0)} г | "
            f"У: {nutrition.get('carbohydrates', 0)} г"
        )
    lines.append("")
    lines.append("Записать приём пищи в дневник?")
    return "\n".join(lines)


def kb_recognition_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Да, верно", callback_data="meal_rec_yes"),
                InlineKeyboardButton("Нет, напишу вручную", callback_data="meal_rec_no"),
            ]
        ]
    )


def kb_save_meal_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Да", callback_data="meal_yes"),
                InlineKeyboardButton("Нет", callback_data="meal_no"),
            ]
        ]
    )


def kb_diary_weight_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Коррекция веса", callback_data="m:dw:fix")],
            [InlineKeyboardButton("⬅ Назад", callback_data="m:diary")],
        ]
    )
