import json
import os
from typing import Dict, Any

from openai import OpenAI
from dotenv import load_dotenv


class LLMAssistant:
    """
    A class to interact with a vision LLM using the OpenAI API.
    Returns ingredients and their weights in grams from a food photo.
    """

    def __init__(
        self,
        system_prompt: str,
        model_id: str = "gpt-4o",
        temperature: float = 0.01,
        max_tokens: int = 1024,
    ):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Environment variable OPENAI_API_KEY is missing or empty."
            )

        self.client = OpenAI(api_key=self.api_key, timeout=60.0)
        self.system_prompt = system_prompt
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_messages(self, image_base64: str) -> list:
        clean_base64 = image_base64.replace("\n", "").replace("\r", "")
        image_url = f"data:image/jpeg;base64,{clean_base64}"
        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.system_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                ],
            }
        ]

    def _parse_response(self, content: str) -> Dict[str, Any]:
        try:
            full_text = (content or "").strip()
            if not full_text:
                return {"status": "success", "result": {}, "error": ""}

            start = full_text.find("{")
            end = full_text.rfind("}")
            if start != -1 and end != -1 and end >= start:
                json_str = full_text[start : end + 1]
                parsed = json.loads(json_str)
                return {"status": "success", "result": parsed, "error": ""}

            return {
                "status": "error",
                "result": {},
                "error": f"No JSON found in response: {full_text[:100]}",
            }
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Failed to parse model output: {e}",
            }

    def generate_response(self, image_base64: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Sends the image and prompt to OpenAI Vision, returns parsed JSON
        (ingredients and weights in grams).
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=self._build_messages(image_base64),
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            choice = response.choices[0] if response.choices else None
            if not choice or not choice.message or not choice.message.content:
                return {
                    "status": "error",
                    "result": {},
                    "error": "Empty response from model",
                }
            return self._parse_response(choice.message.content)
        except Exception as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Process failed: {str(e)}",
            }
