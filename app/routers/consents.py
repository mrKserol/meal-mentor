from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import AI_CHAT_DISCLAIMER_VERSION, CURRENT_DISCLAIMER_VERSION
from app.db.models import User, UserConsent
from app.db.session import get_db
from app.schemas.consents import ConsentAcceptRequest, ConsentAcceptResponse, ConsentStatusResponse

DISCLAIMER_CONSENT_TYPE = "disclaimer"
AI_CHAT_DISCLAIMER_CONSENT_TYPE = "ai_chat_disclaimer"

router = APIRouter(prefix="/api/consents", tags=["consents"])


def _get_current_disclaimer_consent(db: Session, user_id: int) -> UserConsent | None:
    return (
        db.query(UserConsent)
        .filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == DISCLAIMER_CONSENT_TYPE,
            UserConsent.consent_version == CURRENT_DISCLAIMER_VERSION,
        )
        .first()
    )


def get_current_ai_chat_consent(db: Session, user_id: int) -> UserConsent | None:
    return (
        db.query(UserConsent)
        .filter(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == AI_CHAT_DISCLAIMER_CONSENT_TYPE,
            UserConsent.consent_version == AI_CHAT_DISCLAIMER_VERSION,
        )
        .first()
    )


@router.get("/status", response_model=ConsentStatusResponse)
def get_consent_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consent = _get_current_disclaimer_consent(db, current_user.id)

    return ConsentStatusResponse(
        required=consent is None,
        accepted=consent is not None,
        consent_type=DISCLAIMER_CONSENT_TYPE,
        current_version=CURRENT_DISCLAIMER_VERSION,
        accepted_at=consent.accepted_at if consent else None,
    )


@router.post("/accept", response_model=ConsentAcceptResponse)
def accept_consent(
    payload: ConsentAcceptRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.consent_type != DISCLAIMER_CONSENT_TYPE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported consent type")

    if payload.consent_version != CURRENT_DISCLAIMER_VERSION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid disclaimer version")

    existing = _get_current_disclaimer_consent(db, current_user.id)
    if existing:
        return ConsentAcceptResponse(
            accepted=True,
            consent_type=existing.consent_type,
            consent_version=existing.consent_version,
            accepted_at=existing.accepted_at,
        )

    consent = UserConsent(
        user_id=current_user.id,
        consent_type=DISCLAIMER_CONSENT_TYPE,
        consent_version=CURRENT_DISCLAIMER_VERSION,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        extra_metadata={
            "source": "profile_onboarding",
            "language": "ru",
        },
    )

    db.add(consent)
    db.commit()
    db.refresh(consent)

    return ConsentAcceptResponse(
        accepted=True,
        consent_type=consent.consent_type,
        consent_version=consent.consent_version,
        accepted_at=consent.accepted_at,
    )


@router.get("/ai-chat/status")
def get_ai_chat_consent_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    consent = get_current_ai_chat_consent(db, current_user.id)
    return {
        "accepted": consent is not None,
        "consent_type": AI_CHAT_DISCLAIMER_CONSENT_TYPE,
        "consent_version": AI_CHAT_DISCLAIMER_VERSION,
        "accepted_at": consent.accepted_at if consent else None,
    }


@router.post("/ai-chat/accept")
def accept_ai_chat_consent(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = get_current_ai_chat_consent(db, current_user.id)
    if existing:
        return {
            "accepted": True,
            "consent_type": existing.consent_type,
            "consent_version": existing.consent_version,
            "accepted_at": existing.accepted_at,
        }

    consent = UserConsent(
        user_id=current_user.id,
        consent_type=AI_CHAT_DISCLAIMER_CONSENT_TYPE,
        consent_version=AI_CHAT_DISCLAIMER_VERSION,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        extra_metadata={
            "source": "ai_chat",
            "language": current_user.language or "ru",
        },
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return {
        "accepted": True,
        "consent_type": consent.consent_type,
        "consent_version": consent.consent_version,
        "accepted_at": consent.accepted_at,
    }
