"""
Shared data shapes for meal analysis and logging (no Telegram / FastAPI types).
"""

from typing import Any

from pydantic import BaseModel, Field


class MacroTotals(BaseModel):
    """Aggregated macros from nutrition.csv lookup (same keys as legacy API dict)."""

    calories: int = 0
    proteins: int = 0
    fats: int = 0
    carbohydrates: int = 0


class DetectedIngredient(BaseModel):
    """Single line item after vision/normalization (optional structured view)."""

    name: str
    grams: float | None = None


class MealAnalysisResult(BaseModel):
    """Universal result of photo/text meal analysis + optional CSV totals."""

    status: str
    ingredients: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    nutrition: MacroTotals | None = None
    nutrition_full: dict[str, float] | None = None
    prediction: str | None = None
    prediction_translated: str | None = None
    prediction_language: str | None = None
    error: str = ""

    def to_api_dict(self) -> dict[str, Any]:
        """Wire format expected by HTTP API and Streamlit (legacy shape)."""
        out: dict[str, Any] = {
            "status": self.status,
            "ingredients": self.ingredients,
            "confidence": self.confidence,
            "result": self.ingredients,
            "error": self.error,
        }
        if self.prediction is not None:
            out["prediction"] = self.prediction
        if self.prediction_translated is not None:
            out["prediction_translated"] = self.prediction_translated
        if self.prediction_language is not None:
            out["prediction_language"] = self.prediction_language
        if self.nutrition is not None:
            out["nutrition"] = self.nutrition.model_dump()
        if self.nutrition_full is not None:
            out["nutrition_full"] = self.nutrition_full
        return out


class MealLogRequest(BaseModel):
    """Persist confirmed meal (channel-agnostic; telegram_* fields optional for other UIs)."""

    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    ingredients: dict[str, Any] = Field(default_factory=dict)
    source_type: str = "photo"
    telegram_file_id: str | None = None
    prediction: str | None = None
    prediction_translated: str | None = None
    prediction_language: str | None = None
    user_text: str | None = None
    image_base64: str | None = None
    meal_photo_large: str | None = None
    meal_photo_thumb: str | None = None


class MealLogResponse(BaseModel):
    status: str
    error: str = ""

    def to_api_dict(self) -> dict[str, Any]:
        if self.status == "success":
            return {"status": "success"}
        return {"status": "error", "error": self.error}
