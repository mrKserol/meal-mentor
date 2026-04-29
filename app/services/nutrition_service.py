"""Compatibility shim: implementation lives in app.infrastructure.nutrition."""

from app.infrastructure.nutrition.csv_nutrition_provider import NutritionService

__all__ = ["NutritionService"]
