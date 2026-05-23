"""User timezone helpers shared across diary, meals, and additives."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

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


def local_now_in_user_tz(user: User) -> datetime:
    return datetime.now(resolve_tz(user))


def max_meal_local_datetime(user: User) -> datetime:
    """Latest allowed local wall-clock time for scheduling a meal (end of tomorrow)."""
    tz = resolve_tz(user)
    tomorrow = local_now_in_user_tz(user).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(23, 59, 59), tzinfo=tz)


def local_datetime_to_utc_naive(user: User, d: date, t: time) -> datetime:
    tz = resolve_tz(user)
    local_dt = datetime.combine(d, t.replace(second=0, microsecond=0), tzinfo=tz)
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)


def meal_datetime_for_local_date_at_current_time(user: User, d: date) -> datetime:
    """Selected calendar day with the user's current local clock time."""
    now_local = local_now_in_user_tz(user)
    return local_datetime_to_utc_naive(user, d, now_local.time())


def parse_meal_local_datetime_iso(user: User, raw: str) -> datetime:
    """
    Parse `YYYY-MM-DDTHH:mm` (local wall time in user TZ) → UTC-naive for DB.
    Raises ValueError if format is invalid or after end of tomorrow (user TZ).
    """
    value = (raw or "").strip()
    if not value:
        raise ValueError("meal_local_datetime is empty")
    if "T" not in value:
        raise ValueError("meal_local_datetime must be YYYY-MM-DDTHH:mm")
    date_part, time_part = value.split("T", 1)
    d = date.fromisoformat(date_part)
    bits = time_part.split(":")
    if len(bits) < 2:
        raise ValueError("time part must be HH:mm")
    hour = int(bits[0])
    minute = int(bits[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("invalid time")
    tz = resolve_tz(user)
    local_dt = datetime.combine(d, time(hour, minute), tzinfo=tz)
    if local_dt > max_meal_local_datetime(user):
        raise ValueError("meal datetime is after tomorrow")
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)


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
