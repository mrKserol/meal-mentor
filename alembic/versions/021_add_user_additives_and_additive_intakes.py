"""add user additives and additive intakes"""

from alembic import op
import sqlalchemy as sa

from app.db.nutrition_columns import INTEGER_NUTRITION_KEYS, MEAL_ITEM_NUTRITION_KEYS

revision = "021_add_user_additives"
down_revision = "020_curator_assignments"
branch_labels = None
depends_on = None


def _nutrient_columns() -> list[sa.Column]:
    cols: list[sa.Column] = []
    for key in MEAL_ITEM_NUTRITION_KEYS:
        col_type = sa.Integer() if key in INTEGER_NUTRITION_KEYS else sa.Float()
        cols.append(sa.Column(key, col_type, nullable=True))
    return cols


def upgrade() -> None:
    op.create_table(
        "additives",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("additive_name", sa.String(length=255), nullable=False),
        sa.Column("photo_large", sa.String(length=512), nullable=True),
        sa.Column("photo_thumb", sa.String(length=512), nullable=True),
        sa.Column("serving_label", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        *_nutrient_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_additives_user_id", "additives", ["user_id"])

    op.create_table(
        "additive_intakes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("additive_id", sa.Integer(), nullable=True),
        sa.Column("additive_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("servings_count", sa.Float(), nullable=False, server_default="1"),
        sa.Column("intake_datetime", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        *_nutrient_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["additive_id"], ["additives.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_additive_intakes_user_id", "additive_intakes", ["user_id"])
    op.create_index("ix_additive_intakes_additive_id", "additive_intakes", ["additive_id"])
    op.create_index("ix_additive_intakes_intake_datetime", "additive_intakes", ["intake_datetime"])


def downgrade() -> None:
    op.drop_index("ix_additive_intakes_intake_datetime", table_name="additive_intakes")
    op.drop_index("ix_additive_intakes_additive_id", table_name="additive_intakes")
    op.drop_index("ix_additive_intakes_user_id", table_name="additive_intakes")
    op.drop_table("additive_intakes")
    op.drop_index("ix_additives_user_id", table_name="additives")
    op.drop_table("additives")
