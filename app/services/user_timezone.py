"""User timezone helpers shared across diary, meals, and additives."""

from __future__ import annotations

from datetime import date, datetime, time, timezone

import zoneinfo

from app.core.config import BASE_URL
from app.db.models import User


def resolve_tz(user: User) -> zoneinfo.ZoneInfo:
    raw = (user.timezone or "").strip() or "UTC"
    try:
        return zoneinfo.ZoneInfo(raw)
    except Exception:
        return zoneinfo.ZoneInfo("UTC")


def utc_naive_to_local(dt: datetime, tz: zoneinfo.ZoneInfo) -> datetime:
    utc = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    return utc.astimezone(tz)


def meal_datetime_for_local_date_end(user: User, d: date) -> datetime:
    """End of calendar day `d` in user timezone (23:59:59), as UTC-naive for DB."""
    tz = resolve_tz(user)
    local_end = datetime.combine(d, time(23, 59, 59), tzinfo=tz)
    return local_end.astimezone(timezone.utc).replace(tzinfo=None)


def absolute_public_url(web_path: str | None) -> str | None:
    if not web_path:
        return None
    p = web_path.strip()
    if p.startswith("http://") or p.startswith("https://"):
        return p
    base = BASE_URL.rstrip("/")
    if not p.startswith("/"):
        p = "/" + p
    return f"{base}{p}"
