"""Tests for user supplement additives and intakes."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token
from app.db.models import Additive, AdditiveIntake, Base, User
from app.db.session import get_db
from app.main import app
from app.services.additives import get_user_additive, nutrient_payload_from_dict, record_additive_intake
from app.services.additive_totals import sum_additive_intakes_for_local_date
from app.services.additive_ai import _normalize_parsed


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session, monkeypatch):
    monkeypatch.setattr("app.main.init_db", lambda: None)

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _user(db_session, *, email: str = "u@test.com") -> tuple[User, str]:
    user = User(email=email, hashed_password="x", timezone="UTC")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token, _ = create_access_token(user.id)
    return user, token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_additive_whitelist_nutrients(client, db_session):
    user, token = _user(db_session)
    r = client.post(
        "/users/me/additives",
        json={
            "additive_name": "Vitamin C",
            "nutrients": {"vitamin_c_mg": 500, "unknown_field": 99, "protein_g": 0},
        },
        headers=_auth(token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["nutrients"]["vitamin_c_mg"] == 500
    assert "unknown_field" not in data["nutrients"]
    assert "protein_g" not in data["nutrients"]

    row = db_session.query(Additive).filter(Additive.id == data["id"]).first()
    assert row is not None
    assert row.vitamin_c_mg == 500
    assert getattr(row, "unknown_field", None) is None


def test_analyze_additive_unknown_to_ignored(client, db_session):
    _user(db_session)
    _, token = _user(db_session, email="a@test.com")
    mock_result = {
        "status": "success",
        "serving_label": "1 tablet",
        "serving_size_g": None,
        "nutrients": {"vitamin_c_mg": 100},
        "ignored": [{"label": "Foo", "amount": "5g", "reason": "field_not_supported"}],
        "confidence": 0.9,
        "error": None,
    }
    with patch("app.routers.user_additives.analyze_additive_label_from_image_base64", return_value=mock_result):
        r = client.post(
            "/users/me/additives/analyze",
            json={"image_base64": "aGVsbG8="},
            headers=_auth(token),
        )
    assert r.status_code == 200
    body = r.json()
    assert body["nutrients"]["vitamin_c_mg"] == 100
    assert len(body["ignored"]) >= 1


def test_additive_ai_error_status_has_user_friendly_message():
    result = _normalize_parsed({"status": "error"})

    assert result["status"] == "error"
    assert result["error"]
    assert "Unexpected status" not in result["error"]


def test_patch_additive_replaces_nutrients(client, db_session):
    user, token = _user(db_session)
    created = client.post(
        "/users/me/additives",
        json={"additive_name": "Multi", "nutrients": {"vitamin_c_mg": 500, "iron_mg": 10}},
        headers=_auth(token),
    ).json()
    aid = created["id"]
    client.patch(
        f"/users/me/additives/{aid}",
        json={"nutrients": {"vitamin_c_mg": 250}},
        headers=_auth(token),
    )
    row = get_user_additive(db_session, user.id, aid)
    assert row is not None
    assert row.vitamin_c_mg == 250
    assert row.iron_mg is None


def test_soft_delete_additive(client, db_session):
    user, token = _user(db_session)
    created = client.post(
        "/users/me/additives",
        json={"additive_name": "To delete"},
        headers=_auth(token),
    ).json()
    aid = created["id"]
    r = client.delete(f"/users/me/additives/{aid}", headers=_auth(token))
    assert r.status_code == 204
    listed = client.get("/users/me/additives", headers=_auth(token)).json()
    assert all(item["id"] != aid for item in listed["items"])
    row = db_session.query(Additive).filter(Additive.id == aid).first()
    assert row is not None
    assert row.deleted_at is not None


def test_intake_snapshot_not_changed_when_additive_updated(db_session):
    user, _ = _user(db_session)
    add = Additive(user_id=user.id, additive_name="Vit C", vitamin_c_mg=500)
    db_session.add(add)
    db_session.commit()
    db_session.refresh(add)

    intake = record_additive_intake(db_session, user, add.id, servings_count=2)
    assert intake.vitamin_c_mg == 1000

    add.vitamin_c_mg = 100
    db_session.commit()

    db_session.refresh(intake)
    assert intake.vitamin_c_mg == 1000


def test_delete_intake_and_forbidden_other_user(client, db_session):
    user1, token1 = _user(db_session, email="u1@test.com")
    user2, token2 = _user(db_session, email="u2@test.com")
    created = client.post(
        "/users/me/additives",
        json={"additive_name": "X", "nutrients": {"calories": 10}},
        headers=_auth(token1),
    ).json()
    intake = client.post(
        "/users/me/additive-intakes",
        json={"additive_id": created["id"], "servings_count": 1},
        headers=_auth(token1),
    ).json()
    iid = intake["id"]
    r_other = client.delete(f"/users/me/additive-intakes/{iid}", headers=_auth(token2))
    assert r_other.status_code == 404
    r_ok = client.delete(f"/users/me/additive-intakes/{iid}", headers=_auth(token1))
    assert r_ok.status_code == 204
    assert db_session.query(AdditiveIntake).filter(AdditiveIntake.id == iid).first() is None
    _ = user2


def test_water_intake(client, db_session):
    _, token = _user(db_session)
    r = client.post(
        "/users/me/water-intakes",
        json={"amount_ml": 100},
        headers=_auth(token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["additive_name_snapshot"] == "Water"
    assert data["water_g"] == 100


def test_additive_intakes_day_filter(client, db_session):
    user, token = _user(db_session)
    user.timezone = "Europe/Moscow"
    db_session.commit()

    d = date(2026, 5, 20)
    created = client.post(
        "/users/me/additives",
        json={"additive_name": "Day test"},
        headers=_auth(token),
    ).json()
    client.post(
        "/users/me/additive-intakes",
        json={"additive_id": created["id"], "servings_count": 1, "intake_local_date": d.isoformat()},
        headers=_auth(token),
    )

    r = client.get("/users/me/additive-intakes/day", params={"date": d.isoformat()}, headers=_auth(token))
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1

    other = (d + timedelta(days=1)).isoformat()
    r2 = client.get("/users/me/additive-intakes/day", params={"date": other}, headers=_auth(token))
    assert r2.json()["items"] == []


def test_meals_day_additive_totals(client, db_session):
    user, token = _user(db_session)
    d = date.today()
    created = client.post(
        "/users/me/additives",
        json={"additive_name": "Totals", "nutrients": {"calories": 50, "water_g": 0}},
        headers=_auth(token),
    ).json()
    client.post(
        "/users/me/water-intakes",
        json={"amount_ml": 100, "intake_local_date": d.isoformat()},
        headers=_auth(token),
    )
    client.post(
        "/users/me/additive-intakes",
        json={"additive_id": created["id"], "servings_count": 2, "intake_local_date": d.isoformat()},
        headers=_auth(token),
    )
    r = client.get("/users/me/meals/day", params={"date": d.isoformat()}, headers=_auth(token))
    assert r.status_code == 200
    totals = r.json()["additive_totals"]
    assert totals["calories"] == 100
    assert totals["water_g"] == 100


def test_nutrient_payload_from_dict():
    out = nutrient_payload_from_dict({"vitamin_c_mg": "500", "bad": 1, "": 2})
    assert out["vitamin_c_mg"] == 500
    assert "bad" not in out
