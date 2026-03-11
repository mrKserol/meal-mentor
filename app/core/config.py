import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Nutrition CSV (optional)
NUTRITION_CSV_PATH = os.getenv("NUTRITION_CSV_PATH")
if NUTRITION_CSV_PATH:
    _path = Path(NUTRITION_CSV_PATH)
    if not _path.is_absolute():
        _path = Path(__file__).resolve().parent.parent.parent / _path
    NUTRITION_CSV_PATH = str(_path) if _path.exists() else None

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# DB
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./meal_mentor.db",
)
