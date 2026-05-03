"""Add ingredient_state to meal_items for nutrition matching."""

from alembic import op
import sqlalchemy as sa

revision = "010_meal_items_ingredient_state"
down_revision = "009_meal_extra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meal_items", sa.Column("ingredient_state", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("meal_items", "ingredient_state")
