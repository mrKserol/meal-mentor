"""Profile onboarding should seed initial weight measurement."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token
from app.db.models import Base, User, UserMeasurement
from app.db.session import get_db
from app.main import app


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


def _user(db_session, *, email: str = "profile@test.com") -> tuple[User, str]:
    user = User(email=email, hashed_password="x", timezone="UTC")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token, _ = create_access_token(user.id)
    return user, token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_profile_weight_patch_creates_initial_measurement(client, db_session):
    user, token = _user(db_session)

    response = client.patch("/users/me/profile", json={"weight_kg": 82.5}, headers=_auth(token))

    assert response.status_code == 200
    measurements = db_session.query(UserMeasurement).filter(UserMeasurement.user_id == user.id).all()
    assert len(measurements) == 1
    assert measurements[0].weight_kg == 82.5
    assert measurements[0].notes == "weight at check-in"


def test_profile_weight_patch_does_not_duplicate_initial_measurement(client, db_session):
    user, token = _user(db_session)
    client.patch("/users/me/profile", json={"weight_kg": 82.5}, headers=_auth(token))

    response = client.patch("/users/me/profile", json={"weight_kg": 81.0}, headers=_auth(token))

    assert response.status_code == 200
    measurements = db_session.query(UserMeasurement).filter(UserMeasurement.user_id == user.id).all()
    assert len(measurements) == 1
    assert measurements[0].weight_kg == 82.5
