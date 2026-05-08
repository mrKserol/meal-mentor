"""Store meal_item_nutrition.fiber_g as fractional grams (float)."""

from alembic import op
import sqlalchemy as sa

revision = "011_fiber_g_float"
down_revision = "010_meal_items_ingredient_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "meal_item_nutrition",
        "fiber_g",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        postgresql_using="fiber_g::double precision",
    )


def downgrade() -> None:
    op.alter_column(
        "meal_item_nutrition",
        "fiber_g",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        postgresql_using="round(fiber_g)::integer",
    )
