"""Curator assignment and access checks."""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, CuratorUserAssignment, User
from app.routers.curator import _ensure_curator_can_access_user


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _user(db_session, *, email: str, role: str = "user") -> User:
    user = User(email=email, role=role, status="active", timezone="UTC")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_curator_can_access_assigned_user(db_session):
    curator = _user(db_session, email="curator@example.com", role="curator")
    target = _user(db_session, email="user@example.com", role="user")
    db_session.add(CuratorUserAssignment(curator_id=curator.id, user_id=target.id))
    db_session.commit()

    result = _ensure_curator_can_access_user(db_session, curator, target.id)
    assert result.id == target.id


def test_curator_cannot_access_unassigned_user(db_session):
    curator = _user(db_session, email="curator@example.com", role="curator")
    other = _user(db_session, email="other@example.com", role="user")

    with pytest.raises(HTTPException) as exc:
        _ensure_curator_can_access_user(db_session, curator, other.id)
    assert exc.value.status_code == 403


def test_admin_can_access_any_user(db_session):
    admin = _user(db_session, email="admin@example.com", role="admin")
    target = _user(db_session, email="user@example.com", role="user")

    result = _ensure_curator_can_access_user(db_session, admin, target.id)
    assert result.id == target.id
