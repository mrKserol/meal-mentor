"""add nutrition_match_name to meal_items"""

from alembic import op
import sqlalchemy as sa

revision = "022_add_nutrition_match_name"
down_revision = "021_add_user_additives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal_items",
        sa.Column("nutrition_match_name", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meal_items", "nutrition_match_name")
