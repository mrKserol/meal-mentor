"""Load the production entrypoint with real DB drivers, without a PostgreSQL server."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("database_url", "dialect", "driver"),
    [
        ("sqlite:///:memory:", "sqlite", "pysqlite"),
        ("postgresql://test:test@127.0.0.1:1/test", "postgresql", ""),
        ("postgresql+psycopg://test:test@127.0.0.1:1/test", "postgresql", "psycopg"),
        ("postgresql+psycopg2://test:test@127.0.0.1:1/test", "postgresql", "psycopg2"),
    ],
    ids=["sqlite", "postgresql-default", "psycopg", "psycopg2"],
)
def test_api_loads_with_database_driver(tmp_path, database_url, dialect, driver):
    # A fresh interpreter exercises config -> session -> service:app for every URL.
    # PostgreSQL engine creation loads the DBAPI but must not open a connection.
    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "OPENAI_API_KEY": "startup-test-key",
        "JWT_SECRET_KEY": "startup-test-secret",
        "NUTRITION_ENABLE_SEMANTIC": "false",
        "MEAL_PHOTO_UPLOAD_DIR": str(tmp_path / "meal_photos"),
        "ADDITIVE_PHOTO_UPLOAD_DIR": str(tmp_path / "additives"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
from uvicorn import Config

config = Config("service:app")
config.load()
assert config.loaded
assert callable(config.loaded_app)

from app.db.session import engine
assert engine.dialect.name == sys.argv[1]
if sys.argv[2]:
    assert engine.dialect.driver == sys.argv[2]

if engine.dialect.name == "sqlite":
    from fastapi.testclient import TestClient
    from service import app
    with TestClient(app) as client:
        assert client.get("/openapi.json").status_code == 200

engine.dispose()
""",
            dialect,
            driver,
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
