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
from app.services.usage_limits import get_usage_count, increment_usage


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
    monkeypatch.setattr("app.routers.ai_chat.generate_ai_chat_welcome", lambda context: ("Привет! Я Meal-Mentor.", {"model": "test-model"}))
    monkeypatch.setattr(
        "app.routers.ai_chat.generate_ai_chat_reply",
        lambda **kwargs: ("Мягкий ответ Meal-Mentor.", {"model": "test-model", "total_tokens": 12}),
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


def _accept(db_session, user: User) -> None:
    db_session.add(
        UserConsent(
            user_id=user.id,
            consent_type=AI_CHAT_DISCLAIMER_CONSENT_TYPE,
            consent_version=AI_CHAT_DISCLAIMER_VERSION,
            extra_metadata={"source": "test"},
        )
    )
    db_session.commit()


def _enable_ai_chat(db_session, user: User, *, chat_limit: int = 50, ai_limit: int = 100) -> None:
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
                value_int=chat_limit,
            ),
            UserFeatureOverride(
                user_id=user.id,
                feature_key="daily_ai_requests_limit",
                value_type="limit",
                value_int=ai_limit,
            ),
        ]
    )
    db_session.commit()


def test_message_without_ai_chat_consent_returns_403(client, db_session):
    _, token = _user(db_session, email="no-consent@test.com")

    response = client.post("/api/ai-chat/message", json={"message": "Привет"}, headers=_auth(token))

    assert response.status_code == 403


def test_ai_chat_consent_accept_and_bootstrap(client, db_session):
    user, token = _user(db_session, email="consent@test.com")
    _enable_ai_chat(db_session, user)

    before = client.get("/api/ai-chat/bootstrap", headers=_auth(token))
    assert before.status_code == 200
    assert before.json()["disclaimer_required"] is True

    accepted = client.post("/api/consents/ai-chat/accept", json={}, headers=_auth(token))
    assert accepted.status_code == 200
    assert accepted.json()["accepted"] is True
    assert db_session.query(UserConsent).filter(UserConsent.user_id == user.id).count() == 1

    after = client.get("/api/ai-chat/bootstrap", headers=_auth(token))
    assert after.status_code == 200
    body = after.json()
    assert body["disclaimer_required"] is False
    assert body["thread_id"] is not None
    assert body["messages"][0]["role"] == "assistant"
    assert db_session.query(AiChatThread).filter(AiChatThread.user_id == user.id).count() == 1
    assert db_session.query(AiChatMessage).filter(AiChatMessage.user_id == user.id).count() == 1


def test_bootstrap_uses_fallback_welcome_when_openai_unavailable(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.routers.ai_chat.generate_ai_chat_welcome",
        lambda context: (_ for _ in ()).throw(RuntimeError("OpenAI unavailable")),
    )
    user, token = _user(db_session, email="welcome-fallback@test.com")
    _accept(db_session, user)
    _enable_ai_chat(db_session, user)

    response = client.get("/api/ai-chat/bootstrap", headers=_auth(token))

    assert response.status_code == 200
    body = response.json()
    assert body["disclaimer_required"] is False
    assert body["messages"][0]["role"] == "assistant"
    assert "Meal-Mentor" in body["messages"][0]["content"]


def test_message_saves_user_and_assistant_messages_with_medical_risk_context(client, db_session, monkeypatch):
    captured = {}

    def fake_reply(**kwargs):
        captured.update(kwargs)
        return "Обратитесь к специалисту, если симптомы сохраняются.", {"model": "test-model"}

    monkeypatch.setattr("app.routers.ai_chat.generate_ai_chat_reply", fake_reply)
    user, token = _user(db_session, email="risk@test.com")
    _accept(db_session, user)
    _enable_ai_chat(db_session, user)

    response = client.post(
        "/api/ai-chat/message",
        json={"message": "У меня болит живот и плохое самочувствие, что мне пить?"},
        headers=_auth(token),
    )

    assert response.status_code == 200
    assert response.json()["user_message"]["role"] == "user"
    assert response.json()["assistant_message"]["role"] == "assistant"
    assert captured["context"]["risk_context"]["medical_risk_detected"] is True
    assert db_session.query(AiChatMessage).filter(AiChatMessage.user_id == user.id).count() == 2


def test_messages_are_scoped_to_current_user(client, db_session):
    user_a, token_a = _user(db_session, email="a@test.com")
    user_b, token_b = _user(db_session, email="b@test.com")
    _accept(db_session, user_a)
    _accept(db_session, user_b)
    _enable_ai_chat(db_session, user_a)
    _enable_ai_chat(db_session, user_b)

    client.post("/api/ai-chat/message", json={"message": "Сообщение A"}, headers=_auth(token_a))
    client.post("/api/ai-chat/message", json={"message": "Сообщение B"}, headers=_auth(token_b))

    messages_a = client.get("/api/ai-chat/messages", headers=_auth(token_a)).json()["messages"]
    messages_b = client.get("/api/ai-chat/messages", headers=_auth(token_b)).json()["messages"]

    assert any("Сообщение A" in item["content"] for item in messages_a)
    assert not any("Сообщение B" in item["content"] for item in messages_a)
    assert any("Сообщение B" in item["content"] for item in messages_b)


def test_bootstrap_returns_403_when_ai_chat_disabled(client, db_session):
    user, token = _user(db_session, email="disabled@test.com")
    _accept(db_session, user)

    response = client.get("/api/ai-chat/bootstrap", headers=_auth(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "ИИ-чат недоступен на вашем тарифе."


def test_message_returns_403_when_daily_chat_limit_zero(client, db_session):
    user, token = _user(db_session, email="zero-limit@test.com")
    _accept(db_session, user)
    _enable_ai_chat(db_session, user, chat_limit=0)

    response = client.post("/api/ai-chat/message", json={"message": "Привет"}, headers=_auth(token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Дневной лимит сообщений в ИИ-чате исчерпан для вашего тарифа."


def test_message_returns_403_when_daily_chat_limit_exhausted(client, db_session):
    user, token = _user(db_session, email="exhausted@test.com")
    _accept(db_session, user)
    _enable_ai_chat(db_session, user, chat_limit=1)
    increment_usage(
        db_session,
        user.id,
        "daily_ai_chat_messages_limit",
        "daily",
        timezone=user.timezone,
    )

    response = client.post("/api/ai-chat/message", json={"message": "Привет"}, headers=_auth(token))

    assert response.status_code == 403


def test_message_records_usage_after_successful_assistant_response(client, db_session):
    user, token = _user(db_session, email="usage@test.com")
    _accept(db_session, user)
    _enable_ai_chat(db_session, user, chat_limit=5, ai_limit=5)

    response = client.post("/api/ai-chat/message", json={"message": "Привет"}, headers=_auth(token))

    assert response.status_code == 200
    assert get_usage_count(db_session, user.id, "daily_ai_chat_messages_limit", "daily", user.timezone) == 1
    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", user.timezone) == 1


def test_message_does_not_record_usage_when_openai_fails(client, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.routers.ai_chat.generate_ai_chat_reply",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("OpenAI unavailable")),
    )
    user, token = _user(db_session, email="usage-fail@test.com")
    _accept(db_session, user)
    _enable_ai_chat(db_session, user, chat_limit=5, ai_limit=5)

    response = client.post("/api/ai-chat/message", json={"message": "Привет"}, headers=_auth(token))

    assert response.status_code == 503
    assert get_usage_count(db_session, user.id, "daily_ai_chat_messages_limit", "daily", user.timezone) == 0
    assert get_usage_count(db_session, user.id, "daily_ai_requests_limit", "daily", user.timezone) == 0


def test_limits_endpoint_returns_remaining_messages(client, db_session):
    user, token = _user(db_session, email="limits@test.com")
    _enable_ai_chat(db_session, user, chat_limit=5, ai_limit=5)
    increment_usage(
        db_session,
        user.id,
        "daily_ai_chat_messages_limit",
        "daily",
        amount=2,
        timezone=user.timezone,
    )

    response = client.get("/api/ai-chat/limits", headers=_auth(token))

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "daily_limit": 5,
        "used_today": 2,
        "remaining_today": 3,
    }
