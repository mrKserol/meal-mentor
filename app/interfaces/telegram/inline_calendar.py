"""
Inline month calendar for python-telegram-bot (no telebot-calendar dependency).
Callbacks: c:p:YYYY-MM (prev month), c:n:YYYY-MM (next), c:d:YYYY-MM-DD (pick day).
"""

from __future__ import annotations

import calendar
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Short month labels to save callback space
_MONTH_RU = (
    "",
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
)


def _ym_key(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


def birth_date_calendar_keyboard(
    year: int,
    month: int,
    *,
    min_date: date | None = None,
    max_date: date | None = None,
) -> InlineKeyboardMarkup:
    """Full month grid + prev/next. Empty cells use no-op callback 'c:x'."""
    if min_date is None:
        min_date = date(1920, 1, 1)
    if max_date is None:
        max_date = date.today()

    # Clamp view into allowed range
    if date(year, month, 1) > max_date:
        year, month = max_date.year, max_date.month
    if date(year, month, 1) < min_date.replace(day=1):
        year, month = min_date.year, min_date.month

    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    weeks = cal.monthdatescalendar(year, month)

    header = f"{_MONTH_RU[month]} {year}"
    prev_y, prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_y, next_m = (year + 1, 1) if month == 12 else (year, month + 1)

    row_nav = [
        InlineKeyboardButton(
            "«",
            callback_data=f"c:p:{_ym_key(prev_y, prev_m)}",
        ),
        InlineKeyboardButton(header, callback_data="c:x"),
        InlineKeyboardButton(
            "»",
            callback_data=f"c:n:{_ym_key(next_y, next_m)}",
        ),
    ]
    wd = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    row_wd = [InlineKeyboardButton(d, callback_data="c:x") for d in wd]

    rows = [row_nav, row_wd]

    for week in weeks:
        row = []
        for d in week:
            if d.month != month:
                row.append(InlineKeyboardButton(" ", callback_data="c:x"))
                continue
            if d < min_date or d > max_date:
                row.append(InlineKeyboardButton("·", callback_data="c:x"))
                continue
            row.append(
                InlineKeyboardButton(
                    str(d.day),
                    callback_data=f"c:d:{d.isoformat()}",
                )
            )
        rows.append(row)

    rows.append([InlineKeyboardButton("⬅ Назад к профилю", callback_data="m:onb:back")])
    return InlineKeyboardMarkup(rows)
