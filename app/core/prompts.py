from pathlib import Path

from app.core.config import PROMPT_PATH as _PHOTO_PATH, PROMPT2_PATH as _TEXT_PATH

if _PHOTO_PATH and Path(_PHOTO_PATH).exists():
    PHOTO_PROMPT = Path(_PHOTO_PATH).read_text(encoding="utf-8").strip()
else:
    PHOTO_PROMPT = (
        'Return ONLY JSON: {"ingredients": {"name": grams}, "confidence": 0.0-1.0} or {} if no food.'
    )

if _TEXT_PATH and Path(_TEXT_PATH).exists():
    TEXT_PROMPT = Path(_TEXT_PATH).read_text(encoding="utf-8").strip()
else:
    TEXT_PROMPT = PHOTO_PROMPT

# Backward compatibility
VISION_SYSTEM_PROMPT = PHOTO_PROMPT
