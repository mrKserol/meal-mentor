"""
In-memory per-user state for Telegram (FSM).
For multi-instance deploy, replace with Redis or similar.
"""

from typing import Any

USER_STATES: dict[int, dict[str, Any]] = {}


class FlowState:
    """Meal-add pipeline (explicit)."""

    MEAL_ADD_WAITING_INPUT = "meal_add_waiting_input"
    MEAL_ADD_RECOGNITION_CHECK = "meal_add_recognition_check"
    MEAL_ADD_TEXT_MANUAL = "meal_add_text_manual"
    MEAL_ADD_SAVE_CONFIRMATION = "meal_add_save_confirmation"


class UIMode:
    IDLE = "idle"
    DIARY_ADD_MEAL = "diary_add_meal"
