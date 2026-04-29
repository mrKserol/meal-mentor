"""Compatibility shim: implementation lives in app.infrastructure.ai."""

from app.infrastructure.ai.openai_food_client import OpenAIVisionService

__all__ = ["OpenAIVisionService"]
