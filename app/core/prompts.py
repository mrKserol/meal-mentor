from pathlib import Path

from app.core.config import PROMPT_PATH as _PHOTO_PATH, PROMPT2_PATH as _TEXT_PATH

if _PHOTO_PATH and Path(_PHOTO_PATH).exists():
    PHOTO_PROMPT = Path(_PHOTO_PATH).read_text(encoding="utf-8").strip()
else:
    PHOTO_PROMPT = """
Return ONLY valid JSON.

Analyze the food photo and estimate visible ingredients and their weights in grams.

Important portion rule:
1. Estimate ONLY the food currently visible in the image.
2. Do NOT infer the original/full portion size.
3. Do NOT compensate for food that may have already been eaten.
4. If a plate or bowl looks partially eaten, estimate only the visible remaining food.
5. The user will manually add missing/eaten parts if needed.

Food identification rule:
1. Carefully distinguish tuna, beef, chicken, pork, pâté, sausage and other protein foods.
2. If the protein source is uncertain, choose the most visually likely option and lower confidence.
3. For canned/solid tuna, look for flaky dense pink-beige fish texture, compact chunks, and fibrous fish layers.
4. Do not label fish as beef unless there are clear visual signs of meat.

Sauce/dressing rule:
1. Include sauces, dressings, oil, mayo, yogurt sauce, cream sauce or other visible additions if they are visible.
2. If sauce type is uncertain, use "dressing/sauce" and lower confidence.
3. Do not ignore dressing if it visibly remains on the plate, bowl, vegetables or walls of the dish.

Output format:
{
  "prediction": "short human-readable dish name in Russian",
  "ingredients": {
    "ingredient_name": grams
  },
  "confidence": 0.0
}

Example:
If the image shows several chunks of tuna on a plate and only a small remaining part of salad in a bowl, estimate only what is visible now.

Correct:
{
  "prediction": "Тунец с остатком овощного салата",
  "ingredients": {
    "tuna": 140,
    "cucumber": 30,
    "tomato": 20,
    "lettuce": 10,
    "green olives": 10,
    "onion": 5,
    "dressing/sauce": 15
  },
  "confidence": 0.72
}

Incorrect:
- Do not estimate the full original salad portion.
- Do not add vegetables that are not visible.
- Do not classify tuna as beef if the texture looks like canned tuna.
""".strip()

if _TEXT_PATH and Path(_TEXT_PATH).exists():
    TEXT_PROMPT = Path(_TEXT_PATH).read_text(encoding="utf-8").strip()
else:
    TEXT_PROMPT = PHOTO_PROMPT

# Backward compatibility
VISION_SYSTEM_PROMPT = PHOTO_PROMPT
