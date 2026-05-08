"""Add admin roles, plans, features, and subscription plan links."""

from alembic import op
import sqlalchemy as sa

revision = "015_admin_plans_entitlements"
down_revision = "014_nutrient_units_iu"
branch_labels = None
depends_on = None


plans_table = sa.table(
    "plans",
    sa.column("id", sa.Integer),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("price_amount", sa.Integer),
    sa.column("currency", sa.String),
    sa.column("period_days", sa.Integer),
    sa.column("is_active", sa.Boolean),
    sa.column("sort_order", sa.Integer),
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


PLAN_SEED = [
    (
        {"code": "free", "name": "Бесплатный", "description": None, "price_amount": 0, "currency": "RUB", "period_days": 30, "is_active": True, "sort_order": 10},
        {
            "nutrition_diary_enabled": ("Дневник питания", "boolean", True, None, None),
            "food_photo_recognition_enabled": ("Распознавание еды по фото", "boolean", True, None, None),
            "label_analysis_enabled": ("Анализ этикеток", "boolean", False, None, None),
            "ai_chat_enabled": ("ИИ-чат", "boolean", False, None, None),
            "daily_ai_requests_limit": ("Дневной лимит ИИ-запросов", "limit", None, 3, None),
            "monthly_photo_recognition_limit": ("Месячный лимит распознаваний фото", "limit", None, 30, None),
            "monthly_label_analysis_limit": ("Месячный лимит анализов этикеток", "limit", None, 0, None),
            "advanced_nutrients_enabled": ("Расширенные нутриенты", "boolean", False, None, None),
        },
    ),
    (
        {"code": "basic_month", "name": "Базовый", "description": None, "price_amount": 299, "currency": "RUB", "period_days": 30, "is_active": True, "sort_order": 20},
        {
            "nutrition_diary_enabled": ("Дневник питания", "boolean", True, None, None),
            "food_photo_recognition_enabled": ("Распознавание еды по фото", "boolean", True, None, None),
            "label_analysis_enabled": ("Анализ этикеток", "boolean", True, None, None),
            "ai_chat_enabled": ("ИИ-чат", "boolean", True, None, None),
            "daily_ai_requests_limit": ("Дневной лимит ИИ-запросов", "limit", None, 30, None),
            "monthly_photo_recognition_limit": ("Месячный лимит распознаваний фото", "limit", None, 300, None),
            "monthly_label_analysis_limit": ("Месячный лимит анализов этикеток", "limit", None, 100, None),
            "advanced_nutrients_enabled": ("Расширенные нутриенты", "boolean", True, None, None),
        },
    ),
    (
        {"code": "pro_month", "name": "Pro", "description": None, "price_amount": 599, "currency": "RUB", "period_days": 30, "is_active": True, "sort_order": 30},
        {
            "nutrition_diary_enabled": ("Дневник питания", "boolean", True, None, None),
            "food_photo_recognition_enabled": ("Распознавание еды по фото", "boolean", True, None, None),
            "label_analysis_enabled": ("Анализ этикеток", "boolean", True, None, None),
            "ai_chat_enabled": ("ИИ-чат", "boolean", True, None, None),
            "daily_ai_requests_limit": ("Дневной лимит ИИ-запросов", "limit", None, 100, None),
            "monthly_photo_recognition_limit": ("Месячный лимит распознаваний фото", "limit", None, 1000, None),
            "monthly_label_analysis_limit": ("Месячный лимит анализов этикеток", "limit", None, 300, None),
            "advanced_nutrients_enabled": ("Расширенные нутриенты", "boolean", True, None, None),
        },
    ),
]


def upgrade() -> None:
    op.add_column("users", sa.Column("role", sa.String(length=32), nullable=False, server_default="user"))
    op.add_column("users", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_status", "users", ["status"])

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RUB"),
        sa.Column("period_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    op.create_table(
        "plan_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("feature_name", sa.String(length=255), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False, server_default="limit"),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("value_int", sa.Integer(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "feature_key", name="uq_plan_features_plan_key"),
    )
    op.create_index("ix_plan_features_plan_id", "plan_features", ["plan_id"])

    op.create_table(
        "user_feature_overrides",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_key", sa.String(length=64), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False, server_default="limit"),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("value_int", sa.Integer(), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "feature_key", name="uq_user_feature_overrides_user_key"),
    )
    op.create_index("ix_user_feature_overrides_user_id", "user_feature_overrides", ["user_id"])

    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(sa.Column("plan_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("activated_by_admin_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_subscriptions_plan_id", ["plan_id"])
        batch_op.create_foreign_key("fk_subscriptions_plan_id_plans", "plans", ["plan_id"], ["id"])
        batch_op.create_foreign_key(
            "fk_subscriptions_activated_by_admin_id_users",
            "users",
            ["activated_by_admin_id"],
            ["id"],
        )

    bind = op.get_bind()
    for plan, features in PLAN_SEED:
        bind.execute(plans_table.insert().values(**plan))
        plan_id = bind.execute(
            sa.select(plans_table.c.id).where(plans_table.c.code == plan["code"])
        ).scalar_one()
        bind.execute(
            features_table.insert(),
            [
                {
                    "plan_id": plan_id,
                    "feature_key": key,
                    "feature_name": values[0],
                    "value_type": values[1],
                    "value_bool": values[2],
                    "value_int": values[3],
                    "value_text": values[4],
                }
                for key, values in features.items()
            ],
        )


def downgrade() -> None:
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_constraint("fk_subscriptions_activated_by_admin_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_subscriptions_plan_id_plans", type_="foreignkey")
        batch_op.drop_index("ix_subscriptions_plan_id")
        batch_op.drop_column("activated_by_admin_id")
        batch_op.drop_column("plan_id")
    op.drop_index("ix_user_feature_overrides_user_id", table_name="user_feature_overrides")
    op.drop_table("user_feature_overrides")
    op.drop_index("ix_plan_features_plan_id", table_name="plan_features")
    op.drop_table("plan_features")
    op.drop_index("ix_plans_code", table_name="plans")
    op.drop_table("plans")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "status")
    op.drop_column("users", "role")
