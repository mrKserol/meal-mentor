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
                name_translated = v.get("name_translated")
                name_language = v.get("name_language")
                if isinstance(name_translated, str) and name_translated.strip():
                    cleaned[key]["name_translated"] = name_translated.strip()
                if isinstance(name_language, str) and name_language.strip():
                    cleaned[key]["name_language"] = name_language.strip().lower()
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
                "prediction_translated": None,
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
                prediction_translated = None
                prediction_language = None
                if isinstance(raw, dict):
                    p = raw.get("prediction")
                    if isinstance(p, str) and p.strip():
                        prediction = p.strip()
                    pt = raw.get("prediction_translated")
                    if isinstance(pt, str) and pt.strip():
                        prediction_translated = pt.strip()
                    pl = raw.get("prediction_language")
                    if isinstance(pl, str) and pl.strip():
                        prediction_language = pl.strip().lower()
                return {
                    "status": "success",
                    "ingredients": ingredients,
                    "confidence": confidence,
                    "prediction": prediction,
                    "prediction_translated": prediction_translated,
                    "prediction_language": prediction_language,
                    "result": ingredients,
                    "error": "",
                }
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "ingredients": {},
                    "confidence": None,
                    "prediction": None,
                    "prediction_translated": None,
                    "result": {},
                    "error": str(e),
                }
        return {
            "status": "error",
            "ingredients": {},
            "confidence": None,
            "prediction": None,
            "prediction_translated": None,
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
                    "prediction_translated": None,
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
                "prediction_translated": None,
                "result": {},
                "error": str(e),
            }

    def analyze_image_with_user_text(
        self,
        image_base64: str,
        user_text: str,
        previous_ingredients: dict[str, Any] | None = None,
        previous_prediction: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze food using both original photo and user's correction/description.
        Used when initial photo recognition was wrong and user typed clarification.
        """
        try:
            clean = image_base64.replace("\n", "").replace("\r", "")
            url = f"data:image/jpeg;base64,{clean}"

            previous_block = ""
            if previous_prediction or previous_ingredients:
                previous_block = f"""
Previous AI recognition:
prediction: {previous_prediction or ""}

previous_ingredients:
{json.dumps(previous_ingredients or {}, ensure_ascii=False, indent=2)}
""".strip()

            prompt = f"""
{self.photo_prompt}

{previous_block}

User clarification:
"{user_text.strip()}"

Important correction mode:
- The user is correcting the previous AI recognition, not necessarily describing every visible item from scratch.
- Use the user's clarification as the primary hint for the items they mention.
- Keep previously detected ingredients if they are still visible in the image and the user did not explicitly remove or deny them.
- Replace only the ingredients that the user's clarification clearly corrects.
- If the user says "это пшенная каша и орехи фундук", then replace wrong grain/nut identifications, but do not remove visible eggs, cheese, dates, chocolate, sauces or other side items.
- Still use the image to estimate visible ingredients and their weights.
- Estimate ONLY the food currently visible in the image.
- Do NOT infer the original/full portion size.
- Do NOT compensate for food that may have already been eaten.
- Include visible vegetables, fruits, nuts, sweets, sauces, dressings and side ingredients from the image.
- If an item is visible but uncertain, include it with the most likely name and lower confidence.
- Return ONLY valid JSON in the same format:
{{
  "prediction": "short English base dish name",
  "prediction_translated": "short natural dish name in the user's language",
  "prediction_language": "ru",
  "ingredients": {{
    "ingredient_name": {{
      "name_translated": "name in user language",
      "name_language": "ru",
      "grams": 100,
      "state": "cooked"
    }}
  }},
  "confidence": 0.0
}}

Never use translated ingredient names as JSON keys. Ingredient keys must stay in English.

Example:
Previous AI recognition:
prediction: "Кус-кус с яйцами и сыром"
previous_ingredients:
{{
  "couscous": 150,
  "boiled egg": 100,
  "cheese": 30,
  "almonds": 20,
  "dates": 40,
  "chocolate truffle": 15
}}

User clarification:
"это пшеная каша и орехи фундук"

Correct output:
{{
  "prediction": "Millet porridge with eggs, cheese, hazelnuts, dates and chocolate truffle",
  "prediction_translated": "Пшенная каша с яйцами, сыром, фундуком, финиками и шоколадным трюфелем",
  "prediction_language": "ru",
  "ingredients": {{
    "millet porridge": {{"name_translated": "пшенная каша", "name_language": "ru", "grams": 150, "state": "cooked"}},
    "boiled egg": {{"name_translated": "яйцо", "name_language": "ru", "grams": 100, "state": "boiled"}},
    "cheese": {{"name_translated": "сыр", "name_language": "ru", "grams": 30, "state": "unknown"}},
    "hazelnuts": {{"name_translated": "фундук", "name_language": "ru", "grams": 20, "state": "raw"}},
    "dates": {{"name_translated": "финики", "name_language": "ru", "grams": 40, "state": "dry"}},
    "chocolate truffle": {{"name_translated": "шоколадный трюфель", "name_language": "ru", "grams": 15, "state": "unknown"}}
  }},
  "confidence": 0.82
}}

Incorrect:
- Do not remove "chocolate truffle" just because the user did not mention it.
- Do not remove dates, eggs or cheese if they are still visible.
- Do not start the ingredient list from scratch unless the user explicitly says the previous list is completely wrong.
""".strip()

            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
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
                    "prediction_translated": None,
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
                "prediction_translated": None,
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
                    "prediction_translated": None,
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
                "prediction_translated": None,
                "result": {},
                "error": str(e),
            }
