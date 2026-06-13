"""add nutrition pipeline audit fields to meal_items"""

from alembic import op
import sqlalchemy as sa

revision = "028_meal_item_nutrition_pipeline_fields"
down_revision = "027_product_nutrition_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meal_items",
        sa.Column("nutrition_pipeline_version", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "meal_items",
        sa.Column("nutrition_source", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_meal_items_nutrition_pipeline_version",
        "meal_items",
        ["nutrition_pipeline_version"],
    )
    op.create_index(
        "ix_meal_items_nutrition_source",
        "meal_items",
        ["nutrition_source"],
    )


def downgrade() -> None:
    op.drop_index("ix_meal_items_nutrition_source", table_name="meal_items")
    op.drop_index("ix_meal_items_nutrition_pipeline_version", table_name="meal_items")
    op.drop_column("meal_items", "nutrition_source")
    op.drop_column("meal_items", "nutrition_pipeline_version")
