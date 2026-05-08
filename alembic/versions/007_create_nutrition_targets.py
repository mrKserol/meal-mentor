"""Create nutrition_targets table for per-user calculated targets.

Revision ID: 007_nutrition_targets
Revises: 006_users_telegram_bigint
"""

from alembic import op
import sqlalchemy as sa

revision = "007_nutrition_targets"
down_revision = "006_users_telegram_bigint"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def _has_index(bind, table: str, index_name: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(i["name"] == index_name for i in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "nutrition_targets"):
        if not _has_index(bind, "nutrition_targets", "ix_nutrition_targets_user_id"):
            op.create_index("ix_nutrition_targets_user_id", "nutrition_targets", ["user_id"], unique=False)
        return

    op.create_table(
        "nutrition_targets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bmr_kcal", sa.Integer(), nullable=False),
        sa.Column("tdee_kcal", sa.Integer(), nullable=False),
        sa.Column("target_calories", sa.Integer(), nullable=False),
        sa.Column("target_protein_g", sa.Integer(), nullable=False),
        sa.Column("target_fat_g", sa.Integer(), nullable=False),
        sa.Column("target_carbs_g", sa.Integer(), nullable=False),
        sa.Column(
            "formula_name",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'mifflin_st_jeor'"),
        ),
        sa.Column("goal", sa.String(length=100), nullable=True),
        sa.Column("activity_level", sa.String(length=50), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_nutrition_targets_user_id", "nutrition_targets", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_nutrition_targets_user_id", table_name="nutrition_targets")
    op.drop_table("nutrition_targets")
