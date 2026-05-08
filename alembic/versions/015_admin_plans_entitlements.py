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


def _has_table(bind, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_index(bind, table: str, index_name: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(i["name"] == index_name for i in insp.get_indexes(table))


def _has_foreign_key(bind, table: str, local_column: str, referred_table: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    for fk in insp.get_foreign_keys(table):
        if fk.get("referred_table") != referred_table:
            continue
        constrained = fk.get("constrained_columns") or []
        if constrained == [local_column]:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "users", "role"):
        op.add_column("users", sa.Column("role", sa.String(length=32), nullable=False, server_default="user"))
    if not _has_column(bind, "users", "status"):
        op.add_column("users", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))
    if not _has_index(bind, "users", "ix_users_role"):
        op.create_index("ix_users_role", "users", ["role"])
    if not _has_index(bind, "users", "ix_users_status"):
        op.create_index("ix_users_status", "users", ["status"])

    if not _has_table(bind, "plans"):
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
    if not _has_index(bind, "plans", "ix_plans_code"):
        op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    if not _has_table(bind, "plan_features"):
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
    if not _has_index(bind, "plan_features", "ix_plan_features_plan_id"):
        op.create_index("ix_plan_features_plan_id", "plan_features", ["plan_id"])

    if not _has_table(bind, "user_feature_overrides"):
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
    if not _has_index(bind, "user_feature_overrides", "ix_user_feature_overrides_user_id"):
        op.create_index("ix_user_feature_overrides_user_id", "user_feature_overrides", ["user_id"])

    add_plan_id = not _has_column(bind, "subscriptions", "plan_id")
    add_admin_id = not _has_column(bind, "subscriptions", "activated_by_admin_id")
    add_plan_index = not _has_index(bind, "subscriptions", "ix_subscriptions_plan_id")
    add_plan_fk = not _has_foreign_key(bind, "subscriptions", "plan_id", "plans")
    add_admin_fk = not _has_foreign_key(bind, "subscriptions", "activated_by_admin_id", "users")
    if add_plan_id or add_admin_id or add_plan_index or add_plan_fk or add_admin_fk:
        with op.batch_alter_table("subscriptions") as batch_op:
            if add_plan_id:
                batch_op.add_column(sa.Column("plan_id", sa.Integer(), nullable=True))
            if add_admin_id:
                batch_op.add_column(sa.Column("activated_by_admin_id", sa.Integer(), nullable=True))
            if add_plan_index:
                batch_op.create_index("ix_subscriptions_plan_id", ["plan_id"])
            if add_plan_fk:
                batch_op.create_foreign_key("fk_subscriptions_plan_id_plans", "plans", ["plan_id"], ["id"])
            if add_admin_fk:
                batch_op.create_foreign_key(
                    "fk_subscriptions_activated_by_admin_id_users",
                    "users",
                    ["activated_by_admin_id"],
                    ["id"],
                )

    for plan, features in PLAN_SEED:
        plan_id = bind.execute(
            sa.select(plans_table.c.id).where(plans_table.c.code == plan["code"])
        ).scalar_one_or_none()
        if plan_id is None:
            bind.execute(plans_table.insert().values(**plan))
            plan_id = bind.execute(sa.select(plans_table.c.id).where(plans_table.c.code == plan["code"])).scalar_one()
        for key, values in features.items():
            existing_feature = bind.execute(
                sa.select(features_table.c.plan_id).where(
                    features_table.c.plan_id == plan_id,
                    features_table.c.feature_key == key,
                )
            ).first()
            if existing_feature is not None:
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
