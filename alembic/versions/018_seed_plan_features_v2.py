"""Upsert extended plan features (Free / Standard / Pro limits)."""

from alembic import op
import sqlalchemy as sa

revision = "018_seed_plan_features_v2"
down_revision = "017_feature_usage"
branch_labels = None
depends_on = None

plans_table = sa.table(
    "plans",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
)

features_table = sa.table(
    "plan_features",
    sa.column("plan_id", sa.Integer),
    sa.column("feature_key", sa.String),
    sa.column("feature_name", sa.String),
    sa.column("value_type", sa.String),
    sa.column("value_bool", sa.Boolean),
    sa.column("value_int", sa.Integer),
    sa.column("value_text", sa.Text),
)

# (plan_code, feature_key) -> (feature_name, value_type, value_bool, value_int, value_text)
PLAN_FEATURES: dict[str, dict[str, tuple]] = {
    "free": {
        "nutrition_diary_enabled": ("Дневник питания", "boolean", True, None, None),
        "advanced_nutrients_enabled": ("Расширенные нутриенты", "boolean", False, None, None),
        "food_photo_recognition_enabled": ("Распознавание еды по фото", "boolean", True, None, None),
        "label_analysis_enabled": ("Анализ этикеток", "boolean", False, None, None),
        "ai_chat_enabled": ("ИИ-чат", "boolean", False, None, None),
        "allergens_enabled": ("Учет аллергенов", "boolean", False, None, None),
        "daily_ai_requests_limit": ("Дневной лимит ИИ-запросов", "limit", None, 5, None),
        "daily_photo_recognition_limit": ("Дневной лимит распознаваний фото", "limit", None, 3, None),
        "monthly_photo_recognition_limit": ("Месячный лимит распознаваний фото", "limit", None, 30, None),
        "monthly_label_analysis_limit": ("Месячный лимит анализов этикеток", "limit", None, 0, None),
        "daily_ai_chat_messages_limit": ("Дневной лимит сообщений в ИИ-чате", "limit", None, 0, None),
    },
    "basic_month": {
        "nutrition_diary_enabled": ("Дневник питания", "boolean", True, None, None),
        "advanced_nutrients_enabled": ("Расширенные нутриенты", "boolean", True, None, None),
        "food_photo_recognition_enabled": ("Распознавание еды по фото", "boolean", True, None, None),
        "label_analysis_enabled": ("Анализ этикеток", "boolean", True, None, None),
        "ai_chat_enabled": ("ИИ-чат", "boolean", False, None, None),
        "allergens_enabled": ("Учет аллергенов", "boolean", True, None, None),
        "daily_ai_requests_limit": ("Дневной лимит ИИ-запросов", "limit", None, 30, None),
        "daily_photo_recognition_limit": ("Дневной лимит распознаваний фото", "limit", None, 15, None),
        "monthly_photo_recognition_limit": ("Месячный лимит распознаваний фото", "limit", None, 300, None),
        "monthly_label_analysis_limit": ("Месячный лимит анализов этикеток", "limit", None, 30, None),
        "daily_ai_chat_messages_limit": ("Дневной лимит сообщений в ИИ-чате", "limit", None, 0, None),
    },
    "pro_month": {
        "nutrition_diary_enabled": ("Дневник питания", "boolean", True, None, None),
        "advanced_nutrients_enabled": ("Расширенные нутриенты", "boolean", True, None, None),
        "food_photo_recognition_enabled": ("Распознавание еды по фото", "boolean", True, None, None),
        "label_analysis_enabled": ("Анализ этикеток", "boolean", True, None, None),
        "ai_chat_enabled": ("ИИ-чат", "boolean", True, None, None),
        "allergens_enabled": ("Учет аллергенов", "boolean", True, None, None),
        "daily_ai_requests_limit": ("Дневной лимит ИИ-запросов", "limit", None, 100, None),
        "daily_photo_recognition_limit": ("Дневной лимит распознаваний фото", "limit", None, 30, None),
        "monthly_photo_recognition_limit": ("Месячный лимит распознаваний фото", "limit", None, 1000, None),
        "monthly_label_analysis_limit": ("Месячный лимит анализов этикеток", "limit", None, 100, None),
        "daily_ai_chat_messages_limit": ("Дневной лимит сообщений в ИИ-чате", "limit", None, 50, None),
    },
}


def upgrade() -> None:
    bind = op.get_bind()
    for plan_code, features in PLAN_FEATURES.items():
        plan_id = bind.execute(
            sa.select(plans_table.c.id).where(plans_table.c.code == plan_code)
        ).scalar_one_or_none()
        if plan_id is None:
            continue
        for key, values in features.items():
            existing = bind.execute(
                sa.select(features_table.c.plan_id).where(
                    features_table.c.plan_id == plan_id,
                    features_table.c.feature_key == key,
                )
            ).first()
            if existing is not None:
                continue
            bind.execute(
                features_table.insert().values(
                    plan_id=plan_id,
                    feature_key=key,
                    feature_name=values[0],
                    value_type=values[1],
                    value_bool=values[2],
                    value_int=values[3],
                    value_text=values[4],
                )
            )


def downgrade() -> None:
    pass
