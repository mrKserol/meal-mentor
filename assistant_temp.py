import json
from typing import Dict, Any
import os
import base64
import binascii

import replicate
from dotenv import load_dotenv
from fastapi import HTTPException
from replicate.exceptions import ModelError


class LLMAssistant:
    """
    A class to interact with a large language model (LLM) using the Replicate API.
    """

    def __init__(
        self, system_prompt: str, model_id: str, temperature=0.01, max_tokens=1024
    ):
        """
        Initializes the LLMAssistant instance with a system prompt, model ID, temperature, and max tokens.

        Raises:
            ValueError: If the Replicate API token is not set in the environment variables.
        """
        load_dotenv()

        self.token = os.getenv("REPLICATE_API_TOKEN")

        if not self.token:
            raise ValueError(
                "Environment variable REPLICATE_API_TOKEN is missing or empty."
            )

        self.system_prompt = system_prompt
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize replicate client
        self.client = replicate.Client(api_token=self.token)

    def _generate_input(self, image_base64: str) -> Dict[str, Any]:
        """
        Generates the input payload for the model using the Base64-encoded image.
        """
        input = {
            "top_p": 1,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "image": f"data:image/jpeg;base64,{image_base64}",
            "prompt": self.system_prompt,
        }

        return input

    def _parse_response(self, output) -> Dict[str, Any]:
        """
        Parses the model output into a JSON object.
        """
        try:
            # Если output - это путь к файлу (строка), пробуем прочитать его содержимое
            if isinstance(output, str) and output.endswith('.jpg'):
                try:
                    with open(output, 'r') as f:
                        file_content = f.read()
                    # Пробуем парсить содержимое файла как JSON
                    parsed = json.loads(file_content)
                    return {"status": "success", "result": parsed, "error": ""}
                except (json.JSONDecodeError, FileNotFoundError, IOError):
                    # Если не получилось - возвращаем ошибку
                    return {
                        "status": "error",
                        "result": {},
                        "error": f"Model returned file path but could not read/parse it: {output}"
                    }

            # Остальной код парсинга оставляем как есть
            if not isinstance(output, (str, bytes, bytearray, dict, list)):
                output = list(output)

            if isinstance(output, list):
                if len(output) == 0:
                    return {"status": "success", "result": {}, "error": ""}

                last = output[-1]
                if isinstance(last, dict):
                    return {"status": "success", "result": last, "error": ""}

                text = "".join(str(chunk) for chunk in output)
                parsed = json.loads(text)
                return {"status": "success", "result": parsed, "error": ""}

            if isinstance(output, dict):
                return {"status": "success", "result": output, "error": ""}

            if isinstance(output, (bytes, bytearray)):
                output = output.decode("utf-8")

            parsed = json.loads(output)
            return {"status": "success", "result": parsed, "error": ""}

        except Exception as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Failed to parse model output: {e}",
            }

    def generate_response(self, image_base64: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Generates a response from the LLM model using a Base64-encoded image.

        This method sends a request to the model with a Base64-encoded image and system prompt,
        waits for a response, and parses the result. It handles prediction timeouts and response
        parsing, returning the structured output or error details.

        Args:
            image_base64 (str): The Base64-encoded image to be used for generating a response.
            timeout (int, optional): The maximum amount of time (in seconds) to wait for the model's response. Defaults to 10 seconds.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - 'status' (str): 'success' if the process completed successfully, or 'error' if any issues occurred.
                - 'result' (Dict): The parsed model output if successful, or an empty dictionary if an error occurred.
                - 'error' (str): The error message, if any.

        Raises:
            ValueError: If the timeout is less than 1 second.
            TimeoutError: If the prediction process exceeds the specified timeout.

        Internal Methods:
            - `_generate_input`: Prepares the input payload with the Base64 image, system prompt, temperature, and max tokens.
            - `_parse_response`: Converts the raw model output into a structured dictionary, or handles parsing errors.
        """

        try:
            base64.b64decode(image_base64)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="Invalid Base64 image data")

        # 4. Call assistant with error handling
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second")

        try:
            output = replicate.run( f"yorickvp/llava-13b:{self.model_id}",
                input=self._generate_input(image_base64),
                timeout=timeout,
            )
        except ModelError as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Model error: {e}",
            }
        except TimeoutError as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Timeout error: {e}",
            }
        except Exception as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Unexpected error: {e}",
            }

        return self._parse_response(output)