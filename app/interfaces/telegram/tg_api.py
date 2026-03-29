"""HTTP client to local FastAPI (Telegram adapter — no business rules)."""

from __future__ import annotations

from typing import Any, Optional

import requests

from app.core.config import BASE_URL


def _url(path: str) -> str:
    return f"{BASE_URL.rstrip('/')}{path}"


def get_json(path: str, params: Optional[dict[str, Any]] = None, timeout: float = 60) -> Any:
    r = requests.get(_url(path), params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def post_json(path: str, json: Optional[dict[str, Any]] = None, timeout: float = 120) -> Any:
    r = requests.post(_url(path), json=json, timeout=timeout)
    r.raise_for_status()
    return r.json()


def patch_json(
    path: str,
    json: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
    timeout: float = 60,
) -> Any:
    r = requests.patch(_url(path), json=json, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json() if r.content else {}


def patch_params(path: str, params: Optional[dict[str, Any]] = None, timeout: float = 60) -> Any:
    r = requests.patch(_url(path), params=params, timeout=timeout)
    r.raise_for_status()
    return r.json() if r.content else {}


def delete(path: str, params: Optional[dict[str, Any]] = None, timeout: float = 60) -> Any:
    r = requests.delete(_url(path), params=params, timeout=timeout)
    r.raise_for_status()
    return r.json() if r.content else {}


def get_bytes(path: str, params: Optional[dict[str, Any]] = None, timeout: float = 60) -> bytes:
    r = requests.get(_url(path), params=params, timeout=timeout)
    r.raise_for_status()
    return r.content
