"""
In-memory per-user state for Telegram confirmation flow.
For multi-instance deploy, replace with Redis or similar.
"""

from typing import Any

# telegram user_id -> state dict
USER_STATES: dict[int, dict[str, Any]] = {}


class FlowState:
    NONE = "none"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_DESCRIPTION = "awaiting_description"
    AWAITING_CONFIRMATION_AFTER_TEXT = "awaiting_confirmation_after_text"
