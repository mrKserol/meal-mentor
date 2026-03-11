import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
import base64
from typing import Any, Optional

from assistant import LLMAssistant
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Load prompt from file (ingredients + weights in grams)
PROMPT_PATH = Path(__file__).resolve().parent / "promt.txt"
if PROMPT_PATH.exists():
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
else:
    system_prompt = (
        "Identify the food shown in the photo and write the names of specific "
        "ingredients and their weights in grams. Return a JSON object with "
        "ingredient names as keys and weights in grams as numbers. "
        "If the image contains no food, return {}. Return only the JSON object."
    )

assistant = LLMAssistant(system_prompt, temperature=0.01)

# Optional: nutrition lookup from CSV (ingredient -> calories/proteins/fats/carbs per 100g)
NUTRITION_CSV = os.getenv("NUTRITION_CSV_PATH")
if NUTRITION_CSV and Path(NUTRITION_CSV).exists():
    from search import IngredientNutritionSearch
    nutrition_search = IngredientNutritionSearch(NUTRITION_CSV)
else:
    nutrition_search = None


def _aggregate_nutrition(ingredients_weights: dict) -> Optional[dict]:
    """Convert ingredients+weights to total calories, proteins, fats, carbohydrates."""
    if not nutrition_search or not ingredients_weights:
        return None
    try:
        results = nutrition_search.search(ingredients_weights, search_type="fuzzy")
        total = {"calories": 0, "proteins": 0, "fats": 0, "carbohydrates": 0}
        for item in results:
            for _ing, data in item.items():
                if data and isinstance(data, dict):
                    for k in total:
                        total[k] += data.get(k, 0) or 0
        return total
    except Exception:
        return None


@app.post("/generate_response")
async def generate_response(request: Request) -> Any:
    """
    Sends the image to the vision model (OpenAI). Returns ingredients and their
    weights in grams. If NUTRITION_CSV_PATH is set, also returns aggregated
    nutrition (calories, proteins, fats, carbohydrates) for the current UI.
    """
    try:
        data = await request.json()
        image_base64 = data.get("image_base64")

        if not image_base64:
            raise HTTPException(
                status_code=400, detail="Base64 image data is required."
            )

        try:
            base64.b64decode(image_base64)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid Base64 string: {str(e)}"
            ) from e

        result = assistant.generate_response(image_base64)

        if result["status"] != "success":
            return result

        ingredients_weights = result.get("result") or {}
        if not isinstance(ingredients_weights, dict):
            ingredients_weights = {}

        # Optional: add aggregated nutrition for backward compatibility with donut chart
        nutrition = _aggregate_nutrition(ingredients_weights)
        if nutrition is not None:
            result["nutrition"] = nutrition

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        ) from e
