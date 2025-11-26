import json
import time
import os
from typing import Dict, Any

import replicate
from dotenv import load_dotenv


class LLMAssistant:
    """
    A class to interact with a large language model (LLM) using the Replicate API.
    """

    def __init__(
            self, system_prompt: str, model_id: str, temperature=0.01, max_tokens=1024
    ):
        """
        Initializes the LLMAssistant instance.
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

    def _generate_input(self, image_Base64: str) -> Dict[str, Any]:
        """
        Generates the input payload for the model using the Base64-encoded image.
        """
        # Clean Base64
        clean_base64 = image_Base64.replace('\n', '').replace('\r', '')

        input_payload = {
            "top_p": 1,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "image": f"data:image/jpeg;base64,{clean_base64}",
            "prompt": self.system_prompt,
        }

        return input_payload

    def _parse_response(self, output) -> Dict[str, Any]:
        """
        Parses the model output into a JSON object.
        """
        try:
            full_text = ""


            if isinstance(output, str):
                full_text = output
            elif isinstance(output, (list, tuple)) or hasattr(output, '__iter__'):
                full_text = "".join(str(chunk) for chunk in output)


            if isinstance(output, dict):
                return {"status": "success", "result": output, "error": ""}

            # Take JSON
            start_index = full_text.find('{')
            end_index = full_text.rfind('}')

            if start_index != -1 and end_index != -1 and end_index >= start_index:
                json_str = full_text[start_index: end_index + 1]
                parsed = json.loads(json_str)
                return {"status": "success", "result": parsed, "error": ""}
            else:

                if not full_text.strip():
                    return {"status": "success", "result": {}, "error": ""}

                return {
                    "status": "error",
                    "result": {},
                    "error": f"No JSON found in response: {full_text[:100]}"
                }

        except Exception as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Failed to parse model output: {e}",
            }

    def generate_response(self, image_Base64: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Generates a response from the LLM model.
        Uses manual prediction creation and polling to handle timeouts correctly.
        """
        # Validation timeout docstring
        if timeout < 1:
            raise ValueError("Timeout must be at least 1 second")


        try:

            prediction = self.client.predictions.create(
                version=self.model_id,
                input=self._generate_input(image_Base64)
            )


            start_time = time.time()
            while prediction.status not in ["succeeded", "failed", "canceled"]:
                # Timeout checking
                if time.time() - start_time > timeout:
                    prediction.cancel()
                    raise TimeoutError("Prediction timed out")

                time.sleep(0.5)
                prediction.reload()

            if prediction.status == "succeeded":
                return self._parse_response(prediction.output)
            else:
                return {
                    "status": "error",
                    "result": {},
                    "error": f"Model error: {prediction.error}"
                }

        except Exception as e:
            return {
                "status": "error",
                "result": {},
                "error": f"Process failed: {str(e)}",
            }
