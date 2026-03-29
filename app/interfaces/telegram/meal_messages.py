"""Backward-compatible re-exports; prefer telegram_formatters for new code."""

from app.interfaces.telegram.telegram_formatters import (
    format_meal_analyzed_detail as format_meal_reply,
    kb_save_meal_confirm,
)

CONFIRM_KEYBOARD = kb_save_meal_confirm()

__all__ = ["format_meal_reply", "CONFIRM_KEYBOARD"]
