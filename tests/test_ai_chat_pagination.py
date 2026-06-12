from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.security import create_access_token
from app.core.config import AI_CHAT_DISCLAIMER_VERSION
from app.db.models import AiChatMessage, AiChatThread, Base, User, UserConsent, UserFeatureOverride
from app.db.session import get_db
from app.main import app
from app.routers.consents import AI_CHAT_DISCLAIMER_CONSENT_TYPE


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
    monkeypatch.setattr(
        "app.routers.ai_chat.generate_ai_chat_welcome",
        lambda context: ("Привет! Я Meal-Mentor.", {"model": "test-model"}),
    )

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _user(db_session, *, email: str) -> tuple[User, str]:
    user = User(email=email, hashed_password="x", timezone="UTC", language="ru")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token, _ = create_access_token(user.id)
    return user, token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _accept_and_enable(db_session, user: User) -> None:
    db_session.add(
        UserConsent(
            user_id=user.id,
            consent_type=AI_CHAT_DISCLAIMER_CONSENT_TYPE,
            consent_version=AI_CHAT_DISCLAIMER_VERSION,
        )
    )
    db_session.add_all(
        [
            UserFeatureOverride(
                user_id=user.id,
                feature_key="ai_chat_enabled",
                value_type="boolean",
                value_bool=True,
            ),
            UserFeatureOverride(
                user_id=user.id,
                feature_key="daily_ai_chat_messages_limit",
                value_type="limit",
                value_int=50,
            ),
            UserFeatureOverride(
                user_id=user.id,
                feature_key="daily_ai_requests_limit",
                value_type="limit",
                value_int=100,
            ),
        ]
    )
    db_session.commit()


def _thread_with_messages(db_session, user: User, count: int) -> AiChatThread:
    now = datetime.utcnow()
    thread = AiChatThread(user_id=user.id, status="active", created_at=now, updated_at=now)
    db_session.add(thread)
    db_session.flush()
    for idx in range(1, count + 1):
        db_session.add(
            AiChatMessage(
                thread_id=thread.id,
                user_id=user.id,
                role="user" if idx % 2 else "assistant",
                content=f"message {idx}",
                created_at=now + timedelta(seconds=idx),
            )
        )
    db_session.commit()
    db_session.refresh(thread)
    return thread


def test_bootstrap_returns_latest_10_messages_old_to_new(client, db_session):
    user, token = _user(db_session, email="page-bootstrap@test.com")
    _accept_and_enable(db_session, user)
    _thread_with_messages(db_session, user, 15)

    response = client.get("/api/ai-chat/bootstrap", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    contents = [message["content"] for message in body["messages"]]
    assert contents == [f"message {idx}" for idx in range(6, 16)]
    assert body["has_more_messages"] is True
    assert body["oldest_message_id"] == body["messages"][0]["id"]


def test_messages_before_id_returns_older_page(client, db_session):
    user, token = _user(db_session, email="before-id@test.com")
    _accept_and_enable(db_session, user)
    _thread_with_messages(db_session, user, 25)
    first_page = client.get("/api/ai-chat/bootstrap", headers=_auth(token)).json()

    response = client.get(
        f"/api/ai-chat/messages?before_id={first_page['oldest_message_id']}&limit=10",
        headers=_auth(token),
    )

    assert response.status_code == 200
    body = response.json()
    contents = [message["content"] for message in body["messages"]]
    assert contents == [f"message {idx}" for idx in range(6, 16)]
    assert body["has_more"] is True
    assert body["oldest_message_id"] == body["messages"][0]["id"]


def test_messages_endpoint_does_not_return_other_users_messages(client, db_session):
    user_a, token_a = _user(db_session, email="page-a@test.com")
    user_b, _ = _user(db_session, email="page-b@test.com")
    _accept_and_enable(db_session, user_a)
    _accept_and_enable(db_session, user_b)
    _thread_with_messages(db_session, user_a, 3)
    _thread_with_messages(db_session, user_b, 3)

    response = client.get("/api/ai-chat/messages?limit=10", headers=_auth(token_a))

    assert response.status_code == 200
    contents = [message["content"] for message in response.json()["messages"]]
    assert contents == ["message 1", "message 2", "message 3"]


def test_messages_endpoint_returns_empty_without_thread(client, db_session):
    user, token = _user(db_session, email="empty-thread@test.com")
    _accept_and_enable(db_session, user)

    response = client.get("/api/ai-chat/messages?limit=10", headers=_auth(token))

    assert response.status_code == 200
    assert response.json() == {"messages": [], "has_more": False, "oldest_message_id": None}


def test_messages_has_more_false_when_no_older_messages(client, db_session):
    user, token = _user(db_session, email="no-more@test.com")
    _accept_and_enable(db_session, user)
    _thread_with_messages(db_session, user, 8)

    response = client.get("/api/ai-chat/bootstrap", headers=_auth(token))

    assert response.status_code == 200
    assert response.json()["has_more_messages"] is False


def test_sequential_pages_do_not_overlap(client, db_session):
    user, token = _user(db_session, email="no-overlap@test.com")
    _accept_and_enable(db_session, user)
    _thread_with_messages(db_session, user, 22)

    first = client.get("/api/ai-chat/bootstrap", headers=_auth(token)).json()
    second = client.get(
        f"/api/ai-chat/messages?before_id={first['oldest_message_id']}&limit=10",
        headers=_auth(token),
    ).json()
    third = client.get(
        f"/api/ai-chat/messages?before_id={second['oldest_message_id']}&limit=10",
        headers=_auth(token),
    ).json()

    ids = [message["id"] for page in (first["messages"], second["messages"], third["messages"]) for message in page]
    assert len(ids) == len(set(ids))
    assert [message["content"] for message in third["messages"]] == ["message 1", "message 2"]
    assert third["has_more"] is False
