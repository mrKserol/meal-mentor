"""Profile completeness for onboarding vs main menu."""

from app.db.models import User

REQUIRED_ONBOARDING_FIELDS: tuple[str, ...] = (
    "sex",
    "birth_date",
    "height_cm",
    "weight_kg",
    "target_weight_kg",
    "activity_level",
)


def is_profile_complete(user: User | None) -> bool:
    if user is None:
        return False
    return all(getattr(user, f, None) is not None for f in REQUIRED_ONBOARDING_FIELDS)


def missing_profile_fields(user: User | None) -> list[str]:
    if user is None:
        return list(REQUIRED_ONBOARDING_FIELDS)
    return [f for f in REQUIRED_ONBOARDING_FIELDS if getattr(user, f, None) is None]


def get_missing_profile_fields(user: User | None) -> list[str]:
    """Alias for API / clarity (same as missing_profile_fields)."""
    return missing_profile_fields(user)
