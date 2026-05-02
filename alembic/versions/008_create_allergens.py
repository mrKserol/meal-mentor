"""Create allergens table for per-user allergen preferences.

Revision ID: 008_create_allergens
Revises: 007_nutrition_targets
"""

from alembic import op
import sqlalchemy as sa

revision = "008_create_allergens"
down_revision = "007_nutrition_targets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allergens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("allergen_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "allergen_key", name="uq_allergens_user_key"),
    )
    op.create_index("ix_allergens_user_id", "allergens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_allergens_user_id", table_name="allergens")
    op.drop_table("allergens")
