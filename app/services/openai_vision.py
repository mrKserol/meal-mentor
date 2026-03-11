import json
from typing import Any

from openai import OpenAI

from app.core.config import OPENAI_API_KEY, OPENAI_MODEL
from app.core.prompts import VISION_SYSTEM_PROMPT


class OpenAIVisionService:
    """Sends a food photo to OpenAI Vision and returns ingredients + weights (grams) as JSON."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.01,
        max_tokens: int = 1024,
    ):
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=self.api_key, timeout=60.0)
        self.model = model or OPENAI_MODEL
        self.system_prompt = system_prompt or VISION_SYSTEM_PROMPT
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_messages(self, image_base64: str) -> list:
        clean = image_base64.replace("\n", "").replace("\r", "")
        url = f"data:image/jpeg;base64,{clean}"
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.system_prompt},
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            }
        ]

    def _parse_response(self, content: str) -> dict[str, Any]:
        content = (content or "").strip()
        if not content:
            return {"status": "success", "result": {}, "error": ""}
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end >= start:
            try:
                parsed = json.loads(content[start : end + 1])
                return {"status": "success", "result": parsed, "error": ""}
            except json.JSONDecodeError as e:
                return {"status": "error", "result": {}, "error": str(e)}
        return {"status": "error", "result": {}, "error": f"No JSON in response: {content[:100]}"}

    def analyze_image(self, image_base64: str) -> dict[str, Any]:
        """Returns { status, result: { ingredient: weight_g, ... }, error }."""
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self._build_messages(image_base64),
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            choice = resp.choices[0] if resp.choices else None
            if not choice or not choice.message or not choice.message.content:
                return {"status": "error", "result": {}, "error": "Empty model response"}
            return self._parse_response(choice.message.content)
        except Exception as e:
            return {"status": "error", "result": {}, "error": str(e)}
