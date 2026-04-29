import hashlib
import hmac
import time

from app.core.config import TELEGRAM_AUTH_MAX_AGE_SECONDS, TELEGRAM_BOT_TOKEN


def verify_telegram_login(payload: dict[str, str | int]) -> bool:
    """Verify Telegram Login Widget payload signature and freshness."""
    if not TELEGRAM_BOT_TOKEN:
        return False

    raw_hash = str(payload.get("hash", ""))
    auth_date_raw = payload.get("auth_date")
    if not raw_hash or auth_date_raw is None:
        return False

    try:
        auth_date = int(auth_date_raw)
    except (TypeError, ValueError):
        return False

    now = int(time.time())
    if now - auth_date > TELEGRAM_AUTH_MAX_AGE_SECONDS:
        return False

    check_pairs: list[str] = []
    for key, value in payload.items():
        if key in {"hash", "timezone"} or value is None:
            continue
        check_pairs.append(f"{key}={value}")
    check_string = "\n".join(sorted(check_pairs))

    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode("utf-8")).digest()
    calculated_hash = hmac.new(secret_key, check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    return hmac.compare_digest(calculated_hash, raw_hash)
