"""Compatibility shim — implementation: app.interfaces.telegram.telegram_bot."""

from app.interfaces.telegram.telegram_bot import build_application, run_polling, user_states

__all__ = ["build_application", "run_polling", "user_states"]

if __name__ == "__main__":
    run_polling()
