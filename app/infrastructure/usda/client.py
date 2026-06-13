from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.core.config import USDA_API_KEY, USDA_BASE_URL, USDA_REQUEST_TIMEOUT_SECONDS


class UsdaApiError(Exception):
    pass


class UsdaFoodDataClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.api_key = api_key if api_key is not None else USDA_API_KEY
        self.base_url = (base_url or USDA_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else USDA_REQUEST_TIMEOUT_SECONDS

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.api_key:
            raise UsdaApiError("USDA_API_KEY is not configured")

        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        clean_params["api_key"] = self.api_key
        query = urllib.parse.urlencode(clean_params, doseq=True)
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise UsdaApiError("USDA API authentication failed") from exc
            if exc.code == 429:
                raise UsdaApiError("USDA API rate limit exceeded") from exc
            if 500 <= exc.code <= 599:
                raise UsdaApiError("USDA API is temporarily unavailable") from exc
            raise UsdaApiError(f"USDA API request failed with status {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise UsdaApiError("USDA API network error") from exc
        except TimeoutError as exc:
            raise UsdaApiError("USDA API request timed out") from exc
        except json.JSONDecodeError as exc:
            raise UsdaApiError("USDA API returned invalid JSON") from exc
        except Exception as exc:
            raise UsdaApiError("USDA API request failed") from exc

    def search_foods(
        self,
        query: str,
        *,
        data_types: list[str] | None = None,
        page_size: int = 10,
    ) -> dict:
        params: dict[str, Any] = {
            "query": query,
            "pageSize": page_size,
        }
        if data_types:
            params["dataType"] = data_types
        out = self._request_json("/foods/search", params)
        return out if isinstance(out, dict) else {}

    def get_food(self, fdc_id: int) -> dict:
        out = self._request_json(f"/food/{int(fdc_id)}", {})
        return out if isinstance(out, dict) else {}

    def get_foods(self, fdc_ids: list[int]) -> list[dict]:
        foods: list[dict] = []
        for fdc_id in fdc_ids:
            foods.append(self.get_food(fdc_id))
        return foods
