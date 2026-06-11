"""
Vision analysis for supplement/nutrition labels (separate from meal food recognition).
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.core.config import DATA_DIR, OPENAI_API_KEY, OPENAI_MODEL
from app.db.nutrition_columns import MEAL_ITEM_NUTRITION_KEYS


def _prompt_file_path() -> Path:
    return Path(DATA_DIR) / "promt_additive.txt"


def load_additive_prompt() -> str:
    path = _prompt_file_path()
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_json_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(raw, start)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _data_url_for_bytes(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif image_bytes.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    else:
        mime = "image/jpeg"
    return f"data:{mime};base64,{b64}"


def _error_response(error: str) -> dict[str, Any]:
    return {
        "status": "error",
        "serving_label": None,
        "serving_size_g": None,
        "nutrients": {},
        "ignored": [],
        "confidence": None,
        "error": error,
    }


def _filter_nutrients(raw: dict[str, Any]) -> tuple[dict[str, float], list[dict[str, str | None]]]:
    allowed = set(MEAL_ITEM_NUTRITION_KEYS)
    nutrients: dict[str, float] = {}
    ignored: list[dict[str, str | None]] = []
    for key, val in raw.items():
        if key in allowed:
            try:
                nutrients[key] = float(val)
            except (TypeError, ValueError):
                ignored.append(
                    {"label": key, "amount": str(val) if val is not None else None, "reason": "unreadable"},
                )
        else:
            ignored.append(
                {"label": key, "amount": str(val) if val is not None else None, "reason": "field_not_supported"},
            )
    return nutrients, ignored


def _normalize_parsed(parsed: dict[str, Any]) -> dict[str, Any]:
    status = (parsed.get("status") or "").strip().lower()
    if status != "success":
        raw_error = parsed.get("error")
        if isinstance(raw_error, str) and raw_error.strip():
            return _error_response(raw_error.strip())
        return _error_response(
            "Не удалось распознать этикетку. Попробуйте более чёткое фото или заполните добавку вручную.",
        )

    raw_nutrients = parsed.get("nutrients") or {}
    if not isinstance(raw_nutrients, dict):
        raw_nutrients = {}

    nutrients, extra_ignored = _filter_nutrients(raw_nutrients)
    ignored = parsed.get("ignored") or []
    if not isinstance(ignored, list):
        ignored = []
    ignored = list(ignored) + extra_ignored

    serving_size_g = parsed.get("serving_size_g")
    try:
        serving_size_g = float(serving_size_g) if serving_size_g is not None else None
    except (TypeError, ValueError):
        serving_size_g = None

    confidence = parsed.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None

    serving_label = parsed.get("serving_label")
    if serving_label is not None and not isinstance(serving_label, str):
        serving_label = str(serving_label)

    return {
        "status": "success",
        "serving_label": serving_label,
        "serving_size_g": serving_size_g,
        "nutrients": nutrients,
        "ignored": ignored,
        "confidence": confidence,
        "error": None,
    }


def analyze_additive_label_from_image_bytes(image_bytes: bytes) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        return _error_response("OPENAI_API_KEY is not set")

    template = load_additive_prompt()
    allowed_keys = ", ".join(MEAL_ITEM_NUTRITION_KEYS)
    prompt = template.replace("{allowed_nutrient_keys}", allowed_keys)

    client = OpenAI(api_key=OPENAI_API_KEY, timeout=120.0)
    image_url = _data_url_for_bytes(image_bytes)
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=2048,
            temperature=0.2,
        )
        choice = resp.choices[0] if resp.choices else None
        content = (choice.message.content or "").strip() if choice and choice.message else ""
        if not content:
            return _error_response("Пустой ответ модели")
        parsed = extract_json_object(content)
        if parsed is None:
            return _error_response("Не удалось разобрать JSON в ответе модели")
        return _normalize_parsed(parsed)
    except Exception as e:
        return _error_response(str(e))


def analyze_additive_label_from_image_base64(image_base64: str) -> dict[str, Any]:
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except Exception as e:
        return _error_response(f"Invalid base64: {e}")
    if len(image_bytes) > 15 * 1024 * 1024:
        return _error_response("Image too large (max 15 MB)")
    return analyze_additive_label_from_image_bytes(image_bytes)
