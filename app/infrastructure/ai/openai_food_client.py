import json
from typing import Any

from openai import OpenAI

from app.core.config import OPENAI_API_KEY, OPENAI_MODEL
from app.core.prompts import PHOTO_PROMPT, TEXT_PROMPT


def _normalize_model_json(parsed: Any) -> tuple[dict[str, Any], float | None]:
    """
    Model returns either:
      {"ingredients": {"name": grams}, "confidence": 0.85}
      {"ingredients": {"name": {"grams": n, "state": "cooked"}}, ...}
      {} (no food)
    Legacy:
      {"rice": 100, "chicken": 150}
    """
    if not isinstance(parsed, dict):
        return {}, None
    if not parsed:
        return {}, None

    if "ingredients" in parsed:
        ing = parsed["ingredients"]
        if not isinstance(ing, dict):
            ing = {}
        conf = parsed.get("confidence")
        if conf is not None:
            try:
                conf = float(conf)
            except (TypeError, ValueError):
                conf = None
        cleaned: dict[str, Any] = {}
        for k, v in ing.items():
            if not isinstance(k, str) or not k.strip():
                continue
            key = k.strip()
            if isinstance(v, dict):
                g = v.get("grams")
                st = v.get("state", "unknown")
                try:
                    gf = float(g)
                except (TypeError, ValueError):
                    continue
                st_s = str(st).strip().lower() if isinstance(st, str) else "unknown"
                cleaned[key] = {"grams": gf, "state": st_s}
            else:
                try:
                    float(v)
                except (TypeError, ValueError):
                    continue
                cleaned[key] = v
        return cleaned, conf

    # Legacy flat dict: only string keys mapping to numeric-like values
    meta = {"ingredients", "confidence"}
    if meta.isdisjoint(parsed.keys()):
        ingredients: dict[str, Any] = {}
        for k, v in parsed.items():
            if not isinstance(k, str):
                continue
            try:
                float(v)
            except (TypeError, ValueError):
                continue
            ingredients[k] = v
        if ingredients:
            return ingredients, None

    return {}, None


class OpenAIVisionService:
    """OpenAI vision + text meal analysis; unified JSON with ingredients + confidence."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        photo_prompt: str | None = None,
        text_prompt: str | None = None,
        temperature: float = 0.01,
        max_tokens: int = 1024,
    ):
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=self.api_key, timeout=120.0)
        self.model = model or OPENAI_MODEL
        self.photo_prompt = photo_prompt or PHOTO_PROMPT
        self.text_prompt = text_prompt or TEXT_PROMPT
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_photo_messages(self, image_base64: str) -> list:
        clean = image_base64.replace("\n", "").replace("\r", "")
        url = f"data:image/jpeg;base64,{clean}"
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.photo_prompt},
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            }
        ]

    def _parse_content(self, content: str) -> dict[str, Any]:
        content = (content or "").strip()
        if not content:
            return {
                "status": "success",
                "ingredients": {},
                "confidence": None,
                "prediction": None,
                "result": {},
                "error": "",
            }
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end >= start:
            try:
                raw = json.loads(content[start : end + 1])
                ingredients, confidence = _normalize_model_json(raw)
                prediction = None
                if isinstance(raw, dict):
                    p = raw.get("prediction")
                    if isinstance(p, str) and p.strip():
                        prediction = p.strip()
                return {
                    "status": "success",
                    "ingredients": ingredients,
                    "confidence": confidence,
                    "prediction": prediction,
                    "result": ingredients,
                    "error": "",
                }
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "ingredients": {},
                    "confidence": None,
                    "prediction": None,
                    "result": {},
                    "error": str(e),
                }
        return {
            "status": "error",
            "ingredients": {},
            "confidence": None,
            "prediction": None,
            "result": {},
            "error": f"No JSON in response: {content[:100]}",
        }

    def analyze_image(self, image_base64: str) -> dict[str, Any]:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self._build_photo_messages(image_base64),
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            choice = resp.choices[0] if resp.choices else None
            if not choice or not choice.message or not choice.message.content:
                return {
                    "status": "error",
                    "ingredients": {},
                    "confidence": None,
                    "prediction": None,
                    "result": {},
                    "error": "Empty model response",
                }
            return self._parse_content(choice.message.content)
        except Exception as e:
            return {
                "status": "error",
                "ingredients": {},
                "confidence": None,
                "prediction": None,
                "result": {},
                "error": str(e),
            }

    def analyze_text(self, user_text: str) -> dict[str, Any]:
        """Same JSON shape as photo: ingredients + confidence."""
        try:
            body = f"{self.text_prompt}\n\nMeal description:\n{user_text.strip()}"
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": body}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            choice = resp.choices[0] if resp.choices else None
            if not choice or not choice.message or not choice.message.content:
                return {
                    "status": "error",
                    "ingredients": {},
                    "confidence": None,
                    "prediction": None,
                    "result": {},
                    "error": "Empty model response",
                }
            return self._parse_content(choice.message.content)
        except Exception as e:
            return {
                "status": "error",
                "ingredients": {},
                "confidence": None,
                "prediction": None,
                "result": {},
                "error": str(e),
            }
