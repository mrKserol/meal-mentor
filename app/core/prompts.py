from pathlib import Path

from app.core.config import PROMPT_PATH as _PROMPT_PATH

if _PROMPT_PATH and Path(_PROMPT_PATH).exists():
    VISION_SYSTEM_PROMPT = Path(_PROMPT_PATH).read_text(encoding="utf-8").strip()
else:
    VISION_SYSTEM_PROMPT = (
        "Identify the food shown in the photo and write the names of specific "
        "ingredients and their weights in grams. Return a JSON object with "
        "ingredient names as keys and weights in grams as numbers. "
        "If the image contains no food, return {}. Return only the JSON object."
    )
