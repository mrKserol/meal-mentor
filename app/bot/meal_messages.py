from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def format_meal_reply(ingredients: dict[str, Any], nutrition: dict[str, Any] | None) -> str:
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


CONFIRM_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("Да", callback_data="meal_yes"),
            InlineKeyboardButton("Нет", callback_data="meal_no"),
        ]
    ]
)
