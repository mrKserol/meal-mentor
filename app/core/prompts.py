from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "promt.txt"

if PROMPT_PATH.exists():
    VISION_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()
else:
    VISION_SYSTEM_PROMPT = (
        "Identify the food shown in the photo and write the names of specific "
        "ingredients and their weights in grams. Return a JSON object with "
        "ingredient names as keys and weights in grams as numbers. "
        "If the image contains no food, return {}. Return only the JSON object."
    )
