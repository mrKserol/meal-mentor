from datetime import date, datetime
import base64
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import requests
from jose import jwt, JWTError

from app.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expire_at,
    verify_password,
)
from app.auth.telegram import verify_telegram_login
from app.auth.profile import is_profile_completed
from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_BOOTSTRAP_EMAILS,
    TELEGRAM_CLIENT_ID,
    TELEGRAM_CLIENT_SECRET,
    TELEGRAM_REDIRECT_URI,
    YANDEX_CLIENT_ID,
    YANDEX_CLIENT_SECRET,
    YANDEX_REDIRECT_URI,
)
from app.db.models import RefreshToken, User, UserAuthIdentity
from app.schemas.auth import (
    AuthTelegramCallbackRequest,
    AuthTelegramRequest,
    AuthTokenPair,
    AuthYandexCallbackRequest,
)

logger = logging.getLogger(__name__)
TELEGRAM_OIDC_ISSUER = "https://oauth.telegram.org"
TELEGRAM_OIDC_JWKS_URL = "https://oauth.telegram.org/.well-known/jwks.json"


def _admin_bootstrap_emails() -> set[str]:
    return {email.strip().lower() for email in ADMIN_BOOTSTRAP_EMAILS.split(",") if email.strip()}


def apply_admin_bootstrap(db: Session, user: User) -> User:
    """Promote configured first admins by email after a real login."""
    allowed_emails = _admin_bootstrap_emails()
    user_email = (user.email or "").strip().lower()
    if not allowed_emails or not user_email or user_email not in allowed_emails or user.role == "admin":
        return user

    user.role = "admin"
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def _extract_telegram_id(claims: dict) -> int | None:
    candidates = [
        claims.get("id"),
        claims.get("user_id"),
        claims.get("telegram_id"),
    ]
    user_obj = claims.get("user")
    if isinstance(user_obj, dict):
        candidates.append(user_obj.get("id"))

    for value in candidates:
        if value is None:
            continue
        try:
            telegram_id = int(value)
        except (TypeError, ValueError):
            continue
        if telegram_id <= 0:
            continue
        return telegram_id

    return None


def _decode_and_validate_telegram_id_token(id_token: str) -> dict:
    try:
        token_header = jwt.get_unverified_header(id_token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram id_token header") from exc

    kid = token_header.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram id_token missing kid")

    try:
        jwks_response = requests.get(TELEGRAM_OIDC_JWKS_URL, timeout=15)
    except requests.RequestException as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Telegram JWKS") from exc

    if jwks_response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch Telegram JWKS")

    jwks_payload = jwks_response.json()
    keys = jwks_payload.get("keys") if isinstance(jwks_payload, dict) else None
    if not isinstance(keys, list):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid Telegram JWKS payload")

    signing_key = next((k for k in keys if isinstance(k, dict) and k.get("kid") == kid), None)
    if not signing_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No matching Telegram JWKS key")

    try:
        claims = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=str(TELEGRAM_CLIENT_ID),
            issuer=TELEGRAM_OIDC_ISSUER,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram id_token claims") from exc

    return claims


def _parse_yandex_birth_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip()

    try:
        return date.fromisoformat(raw)
    except ValueError:
        logger.warning("Unsupported Yandex birthday format: %s", raw)
        return None


def _normalize_yandex_sex(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    raw = value.strip().lower()

    if raw in {"male", "m", "man", "мужской"}:
        return "male"
    if raw in {"female", "f", "woman", "женский"}:
        return "female"

    logger.warning("Unsupported Yandex sex value: %s", raw)
    return None


def get_user_by_identity(
    db: Session,
    *,
    provider: str,
    provider_user_id: str,
) -> User | None:
    identity = (
        db.query(UserAuthIdentity)
        .filter(
            UserAuthIdentity.provider == provider,
            UserAuthIdentity.provider_user_id == str(provider_user_id),
        )
        .first()
    )
    return identity.user if identity else None


def attach_identity_to_user(
    db: Session,
    *,
    user: User,
    provider: str,
    provider_user_id: str,
    email: str | None = None,
    username: str | None = None,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> UserAuthIdentity:
    existing = (
        db.query(UserAuthIdentity)
        .filter(
            UserAuthIdentity.provider == provider,
            UserAuthIdentity.provider_user_id == str(provider_user_id),
        )
        .first()
    )
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This external account is already linked to another user",
            )
        return existing

    identity = UserAuthIdentity(
        user_id=user.id,
        provider=provider,
        provider_user_id=str(provider_user_id),
        email=email,
        username=username,
        display_name=display_name,
        avatar_url=avatar_url,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity


def get_or_create_telegram_user(
    db: Session,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    timezone: str | None = None,
) -> tuple[User, bool]:
    provider_user_id = str(telegram_id)

    user = get_user_by_identity(
        db,
        provider="telegram",
        provider_user_id=provider_user_id,
    )
    if user:
        return user, False

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        attach_identity_to_user(
            db,
            user=user,
            provider="telegram",
            provider_user_id=provider_user_id,
            username=username,
            display_name=first_name,
        )
        return user, False

    logger.info("creating new web telegram user")
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        timezone=timezone or "UTC",
        subscription_status="Free",
        email=None,
        hashed_password=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("new user created id: %s", user.id)

    attach_identity_to_user(
        db,
        user=user,
        provider="telegram",
        provider_user_id=provider_user_id,
        username=username,
        display_name=first_name,
    )

    return user, True


def register_user(
    db: Session,
    *,
    telegram_username: str | None,
    first_name: str | None,
    sex: str | None,
    birth_date: date | None,
    height_cm: int | None,
    weight_kg: float | None,
    goal: str | None,
    activity_level: str | None,
    target_weight_kg: float | None,
    timezone: str | None,
    email: str,
    password: str,
) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        username=telegram_username,
        first_name=first_name,
        sex=sex,
        birth_date=birth_date,
        height_cm=height_cm,
        weight_kg=weight_kg,
        goal=goal,
        activity_level=activity_level,
        target_weight_kg=target_weight_kg,
        timezone=timezone,
        hashed_password=hash_password(password),
        subscription_status="Free",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, *, email: str, password: str) -> tuple[User, AuthTokenPair]:
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user = apply_admin_bootstrap(db, user)
    return user, _issue_token_pair(db, user)


def login_with_telegram(db: Session, payload: AuthTelegramRequest) -> tuple[User, AuthTokenPair]:
    raw_payload = payload.model_dump()
    if not verify_telegram_login(raw_payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram auth payload")

    user, _ = get_or_create_telegram_user(
        db,
        telegram_id=int(payload.id),
        username=payload.username,
        first_name=payload.first_name,
        timezone=payload.timezone,
    )
    user = apply_admin_bootstrap(db, user)

    return user, _issue_token_pair(db, user)


def login_with_telegram_oauth(
    db: Session, payload: AuthTelegramCallbackRequest
) -> tuple[User, AuthTokenPair, bool, bool]:
    logger.info("telegram callback started")
    if not TELEGRAM_CLIENT_ID or not TELEGRAM_CLIENT_SECRET or not TELEGRAM_REDIRECT_URI:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Telegram OAuth is not configured")

    basic_creds = base64.b64encode(f"{TELEGRAM_CLIENT_ID}:{TELEGRAM_CLIENT_SECRET}".encode("utf-8")).decode("utf-8")
    token_response = requests.post(
        "https://oauth.telegram.org/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_creds}",
        },
        data={
            "grant_type": "authorization_code",
            "client_id": TELEGRAM_CLIENT_ID,
            "code": payload.code,
            "redirect_uri": payload.redirect_uri,
            "code_verifier": payload.code_verifier,
        },
        timeout=15,
    )
    if token_response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram code exchange failed")
    logger.info("telegram token exchange success")

    token_data = token_response.json()
    id_token = token_data.get("id_token")
    if not isinstance(id_token, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram id_token missing in token response")
    claims = _decode_and_validate_telegram_id_token(id_token)

    logger.info("telegram userinfo keys: %s", sorted(list(claims.keys())))
    logger.info("sub claim present: %s (ignored for telegram_id)", "sub" in claims)
    logger.info(
        "telegram id candidates present: id=%s user_id=%s telegram_id=%s nested_user_id=%s",
        claims.get("id") is not None,
        claims.get("user_id") is not None,
        claims.get("telegram_id") is not None,
        isinstance(claims.get("user"), dict) and claims.get("user", {}).get("id") is not None,
    )
    telegram_id = _extract_telegram_id(claims)
    logger.info("telegram_id parsed: %s", telegram_id)
    if telegram_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram user id not found in OAuth claims")

    first_name = claims.get("name") or claims.get("given_name") or claims.get("first_name")
    username = claims.get("preferred_username") or claims.get("username")
    email = claims.get("email") if isinstance(claims.get("email"), str) else None

    user, is_new_user = get_or_create_telegram_user(
        db,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        timezone=payload.timezone,
    )
    if email and not user.email:
        user.email = email
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    user = apply_admin_bootstrap(db, user)

    profile_completed = is_profile_completed(user)
    logger.info("profile_completed value: %s", profile_completed)
    return user, _issue_token_pair(db, user), is_new_user, profile_completed


def login_with_yandex_oauth(
    db: Session,
    payload: AuthYandexCallbackRequest,
) -> tuple[User, AuthTokenPair, bool, bool]:
    logger.info("yandex callback started")

    if not YANDEX_CLIENT_ID or not YANDEX_CLIENT_SECRET or not YANDEX_REDIRECT_URI:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Yandex OAuth is not configured",
        )

    token_response = requests.post(
        "https://oauth.yandex.ru/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": payload.code,
            "client_id": YANDEX_CLIENT_ID,
            "client_secret": YANDEX_CLIENT_SECRET,
            "redirect_uri": payload.redirect_uri,
        },
        timeout=15,
    )

    if token_response.status_code >= 400:
        logger.warning("Yandex token exchange failed: %s", token_response.text[:500])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yandex code exchange failed",
        )

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yandex access_token missing in token response",
        )

    userinfo_response = requests.get(
        "https://login.yandex.ru/info",
        headers={"Authorization": f"OAuth {access_token}"},
        params={"format": "json"},
        timeout=15,
    )

    if userinfo_response.status_code >= 400:
        logger.warning("Yandex userinfo failed: %s", userinfo_response.text[:500])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yandex userinfo request failed",
        )

    profile = userinfo_response.json()
    if not isinstance(profile, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yandex userinfo response invalid",
        )

    logger.info("yandex userinfo keys: %s", sorted(profile.keys()))

    def _as_str(v: object) -> str | None:
        return v.strip() if isinstance(v, str) and v.strip() else None

    yandex_id = profile.get("id")
    if yandex_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yandex user id not found",
        )

    provider_user_id = str(yandex_id)
    email = _as_str(profile.get("default_email"))
    username = _as_str(profile.get("login"))
    first_name = _as_str(profile.get("first_name"))
    display_name = (
        _as_str(profile.get("display_name"))
        or _as_str(profile.get("real_name"))
        or first_name
        or username
    )

    avatar_url = None
    avatar_id = profile.get("default_avatar_id")
    if isinstance(avatar_id, str) and avatar_id:
        avatar_url = f"https://avatars.yandex.net/get-yapic/{avatar_id}/islands-200"

    birth_date = _parse_yandex_birth_date(profile.get("birthday"))
    sex = _normalize_yandex_sex(profile.get("sex"))

    user = get_user_by_identity(
        db,
        provider="yandex",
        provider_user_id=provider_user_id,
    )

    is_new_user = False

    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if user:
        attach_identity_to_user(
            db,
            user=user,
            provider="yandex",
            provider_user_id=provider_user_id,
            email=email,
            username=username,
            display_name=display_name,
            avatar_url=avatar_url,
        )

        changed = False
        if email and not user.email:
            user.email = email
            changed = True
        if first_name and not user.first_name:
            user.first_name = first_name
            changed = True
        if sex and not user.sex:
            user.sex = sex
            changed = True
        if birth_date and not user.birth_date:
            user.birth_date = birth_date
            changed = True
        if payload.timezone and not user.timezone:
            user.timezone = payload.timezone
            changed = True
        if changed:
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
    else:
        user = User(
            email=email,
            username=username,
            first_name=first_name or display_name,
            sex=sex,
            birth_date=birth_date,
            timezone=payload.timezone or "UTC",
            subscription_status="Free",
            hashed_password=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        attach_identity_to_user(
            db,
            user=user,
            provider="yandex",
            provider_user_id=provider_user_id,
            email=email,
            username=username,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        is_new_user = True

    user = apply_admin_bootstrap(db, user)
    profile_completed = is_profile_completed(user)

    return user, _issue_token_pair(db, user), is_new_user, profile_completed


def refresh_tokens(db: Session, *, refresh_token: str) -> AuthTokenPair:
    token_hash = hash_refresh_token(refresh_token)
    token_row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not token_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    now = datetime.utcnow()
    if token_row.revoked_at is not None or token_row.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    user = db.query(User).filter(User.id == token_row.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_refresh_plain = generate_refresh_token()
    new_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh_plain),
        expires_at=refresh_token_expire_at(),
    )
    db.add(new_refresh)
    db.flush()

    token_row.revoked_at = now
    token_row.replaced_by_token_id = new_refresh.id

    access_token, _ = create_access_token(user.id)
    db.commit()
    return AuthTokenPair(
        access_token=access_token,
        refresh_token=new_refresh_plain,
        access_token_expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def logout_user(db: Session, *, refresh_token: str) -> None:
    token_hash = hash_refresh_token(refresh_token)
    token_row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if token_row and token_row.revoked_at is None:
        token_row.revoked_at = datetime.utcnow()
        db.commit()


def _issue_token_pair(db: Session, user: User) -> AuthTokenPair:
    access_token, _ = create_access_token(user.id)
    refresh_plain = generate_refresh_token()
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_plain),
        expires_at=refresh_token_expire_at(),
    )
    db.add(refresh_row)
    db.commit()
    return AuthTokenPair(
        access_token=access_token,
        refresh_token=refresh_plain,
        access_token_expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
