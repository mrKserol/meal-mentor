"""
Legacy entrypoint: uvicorn service:app still runs the full API.
The main app lives in app.main.
"""
from app.main import app

__all__ = ["app"]
