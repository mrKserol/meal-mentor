from __future__ import annotations

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import AI_CHAT_DISCLAIMER_VERSION, OPENAI_CHAT_MODEL
from app.db.models import AiChatMessage, AiChatThread, User
from app.db.session import get_db
from app.routers.consents import get_current_ai_chat_consent
from app.schemas.ai_chat import AiChatBootstrapResponse, AiChatMessageResponse, AiChatSendRequest, AiChatSendResponse
from app.services.ai_chat_context import build_ai_chat_context
from app.services.ai_chat_llm import generate_ai_chat_reply, generate_ai_chat_welcome
from app.services.ai_chat_safety import detect_medical_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai-chat", tags=["ai-chat"])


def _message_response(row: AiChatMessage) -> AiChatMessageResponse:
    return AiChatMessageResponse.from_orm(row)


def _has_ai_chat_consent(db: Session, user_id: int) -> bool:
    return get_current_ai_chat_consent(db, user_id) is not None


def get_or_create_active_thread(db: Session, user_id: int) -> AiChatThread:
    thread = (
        db.query(AiChatThread)
        .filter(AiChatThread.user_id == user_id, AiChatThread.status == "active")
        .order_by(AiChatThread.updated_at.desc(), AiChatThread.id.desc())
        .first()
    )
    if thread is not None:
        return thread
    now = datetime.utcnow()
    thread = AiChatThread(user_id=user_id, status="active", created_at=now, updated_at=now)
    db.add(thread)
    db.flush()
    return thread


def _recent_messages(db: Session, thread_id: int, limit: int) -> list[AiChatMessage]:
    rows = (
        db.query(AiChatMessage)
        .filter(AiChatMessage.thread_id == thread_id)
        .order_by(AiChatMessage.created_at.desc(), AiChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def _llm_history(rows: list[AiChatMessage]) -> list[dict]:
    return [
        {"role": row.role, "content": row.content}
        for row in rows
        if row.role in {"user", "assistant", "system"} and row.content
    ]


def _add_message(
    db: Session,
    *,
    thread: AiChatThread,
    user_id: int,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> AiChatMessage:
    now = datetime.utcnow()
    message = AiChatMessage(
        thread_id=thread.id,
        user_id=user_id,
        role=role,
        content=content,
        model=(metadata or {}).get("model"),
        prompt_tokens=(metadata or {}).get("prompt_tokens"),
        completion_tokens=(metadata or {}).get("completion_tokens"),
        total_tokens=(metadata or {}).get("total_tokens"),
        extra_metadata=metadata or {},
        created_at=now,
    )
    thread.last_message_at = now
    thread.updated_at = now
    db.add(message)
    db.add(thread)
    db.flush()
    return message


@router.get("/bootstrap", response_model=AiChatBootstrapResponse)
def bootstrap_ai_chat(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _has_ai_chat_consent(db, current_user.id):
        return AiChatBootstrapResponse(
            thread_id=None,
            disclaimer_required=True,
            disclaimer_version=AI_CHAT_DISCLAIMER_VERSION,
            messages=[],
        )

    thread = get_or_create_active_thread(db, current_user.id)
    messages = _recent_messages(db, thread.id, limit=50)
    if not messages:
        context = build_ai_chat_context(db, current_user)
        try:
            content, meta = generate_ai_chat_welcome(context)
        except Exception as exc:
            logger.exception("AI chat welcome generation failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Не удалось загрузить чат. Попробуйте позже.",
            ) from exc
        meta = {**meta, "kind": "welcome"}
        welcome = _add_message(
            db,
            thread=thread,
            user_id=current_user.id,
            role="assistant",
            content=content,
            metadata=meta,
        )
        db.commit()
        db.refresh(welcome)
        messages = [welcome]
    else:
        db.commit()

    return AiChatBootstrapResponse(
        thread_id=thread.id,
        disclaimer_required=False,
        disclaimer_version=AI_CHAT_DISCLAIMER_VERSION,
        messages=[_message_response(row) for row in messages],
    )


@router.post("/message", response_model=AiChatSendResponse)
def send_ai_chat_message(
    payload: AiChatSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _has_ai_chat_consent(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI Chat disclaimer is required")

    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="message is required")

    thread = get_or_create_active_thread(db, current_user.id)
    previous_rows = _recent_messages(db, thread.id, limit=20)
    user_message = _add_message(
        db,
        thread=thread,
        user_id=current_user.id,
        role="user",
        content=text,
        metadata={"kind": "user_message"},
    )
    db.commit()
    db.refresh(user_message)

    context = build_ai_chat_context(db, current_user)
    context["risk_context"] = detect_medical_risk(text)

    try:
        content, meta = generate_ai_chat_reply(
            user_message=text,
            context=context,
            previous_messages=_llm_history(previous_rows),
        )
    except Exception as exc:
        logger.exception("AI chat reply generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Не удалось получить ответ Meal-Mentor. Попробуйте ещё раз.",
        ) from exc

    meta = {**meta, "kind": "assistant_message", "model": meta.get("model") or OPENAI_CHAT_MODEL}
    assistant_message = _add_message(
        db,
        thread=thread,
        user_id=current_user.id,
        role="assistant",
        content=content,
        metadata=meta,
    )
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return AiChatSendResponse(
        thread_id=thread.id,
        user_message=_message_response(user_message),
        assistant_message=_message_response(assistant_message),
    )


@router.get("/messages", response_model=list[AiChatMessageResponse])
def list_ai_chat_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _has_ai_chat_consent(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI Chat disclaimer is required")
    thread = get_or_create_active_thread(db, current_user.id)
    messages = _recent_messages(db, thread.id, limit=50)
    db.commit()
    return [_message_response(row) for row in messages]
