import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", REPO_ROOT / "data"))

# API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Prompts (optional env override)
_default_prompt = DATA_DIR / "promt.txt"
_prompt_env = os.getenv("PROMPT_PATH")
_prompt_candidate = Path(_prompt_env) if _prompt_env else _default_prompt
if not _prompt_candidate.is_absolute():
    _prompt_candidate = REPO_ROOT / _prompt_candidate
if _prompt_candidate.exists():
    PROMPT_PATH = str(_prompt_candidate)
else:
    _fallback = _default_prompt
    if not _fallback.is_absolute():
        _fallback = REPO_ROOT / _fallback
    PROMPT_PATH = str(_fallback) if _fallback.exists() else None

_default_text_prompt = DATA_DIR / "promt2.txt"
_text_prompt_env = os.getenv("PROMPT2_PATH")
_text_prompt_candidate = Path(_text_prompt_env) if _text_prompt_env else _default_text_prompt
if not _text_prompt_candidate.is_absolute():
    _text_prompt_candidate = REPO_ROOT / _text_prompt_candidate
if _text_prompt_candidate.exists():
    PROMPT2_PATH = str(_text_prompt_candidate)
else:
    _tfb = _default_text_prompt
    if not _tfb.is_absolute():
        _tfb = REPO_ROOT / _tfb
    PROMPT2_PATH = str(_tfb) if _tfb.exists() else None

try:
    LOW_CONFIDENCE_THRESHOLD = float(os.getenv("LOW_CONFIDENCE_THRESHOLD", "0.5"))
except ValueError:
    LOW_CONFIDENCE_THRESHOLD = 0.5

# Nutrition CSV (optional)
_default_nutrition = DATA_DIR / "nutrition.csv"
_nutrition_env = os.getenv("NUTRITION_CSV_PATH")
_nutrition_candidate = Path(_nutrition_env) if _nutrition_env else _default_nutrition
if not _nutrition_candidate.is_absolute():
    _nutrition_candidate = REPO_ROOT / _nutrition_candidate
if _nutrition_candidate.exists():
    NUTRITION_CSV_PATH = str(_nutrition_candidate)
else:
    # If env path is stale/missing, fall back to default if present
    _fallback = _default_nutrition
    if not _fallback.is_absolute():
        _fallback = REPO_ROOT / _fallback
    NUTRITION_CSV_PATH = str(_fallback) if _fallback.exists() else None

_default_aliases = DATA_DIR / "food_aliases.json"
_aliases_env = os.getenv("FOOD_ALIASES_PATH")
_aliases_candidate = Path(_aliases_env) if _aliases_env else _default_aliases
if not _aliases_candidate.is_absolute():
    _aliases_candidate = REPO_ROOT / _aliases_candidate
if _aliases_candidate.exists():
    FOOD_ALIASES_PATH = str(_aliases_candidate)
else:
    _afb = _default_aliases
    if not _afb.is_absolute():
        _afb = REPO_ROOT / _afb
    FOOD_ALIASES_PATH = str(_afb) if _afb.exists() else None

# If true, sentence-transformers may download from huggingface.co on first semantic search.
# Default false: production (Railway) often times out on HF; fuzzy matching needs no download.
NUTRITION_ENABLE_SEMANTIC = os.getenv("NUTRITION_ENABLE_SEMANTIC", "false").lower() in (
    "1",
    "true",
    "yes",
)

# Nutrition matching: INFO logs with top candidates per ingredient (see NutritionService).
# Read at runtime via nutrition_debug_matching() so tests can toggle os.environ without reload.
def nutrition_debug_matching() -> bool:
    return os.getenv("NUTRITION_DEBUG_MATCHING", "0").lower() in ("1", "true", "yes")


# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_AUTH_MAX_AGE_SECONDS = int(os.getenv("TELEGRAM_AUTH_MAX_AGE_SECONDS", "86400"))
TELEGRAM_CLIENT_ID = os.getenv("TELEGRAM_CLIENT_ID")
TELEGRAM_CLIENT_SECRET = os.getenv("TELEGRAM_CLIENT_SECRET")
TELEGRAM_REDIRECT_URI = os.getenv("TELEGRAM_REDIRECT_URI")

# Subscriptions: if true, POST /subscriptions/order activates plan without Robokassa (demo only)
SUBSCRIPTION_DEMO_AUTO = os.getenv("SUBSCRIPTION_DEMO_AUTO", "0").lower() in ("1", "true", "yes")

# DB
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./meal_mentor.db",
)

# Meal photos on disk; DB stores web paths /media/meal_photos/... only (not absolute filesystem paths)
MEAL_PHOTO_UPLOAD_DIR = Path(os.getenv("MEAL_PHOTO_UPLOAD_DIR", "data/uploads/meal_photos"))
if not MEAL_PHOTO_UPLOAD_DIR.is_absolute():
    MEAL_PHOTO_UPLOAD_DIR = REPO_ROOT / MEAL_PHOTO_UPLOAD_DIR

# Auth / JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
ADMIN_BOOTSTRAP_EMAILS = os.getenv("ADMIN_BOOTSTRAP_EMAILS", "")
