from app.db.models import User

REQUIRED_PROFILE_FIELDS: tuple[str, ...] = (
    "sex",
    "birth_date",
    "height_cm",
    "weight_kg",
    "goal",
    "activity_level",
    "target_weight_kg",
)


def is_profile_completed(user: User | None) -> bool:
    if user is None:
        return False
    return all(getattr(user, field, None) is not None for field in REQUIRED_PROFILE_FIELDS)
