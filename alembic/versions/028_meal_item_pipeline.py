"""add nutrition pipeline audit fields to meal_items"""

from alembic import op
import sqlalchemy as sa

revision = "028_meal_item_pipeline"
down_revision = "027_product_nutrition_cache"
branch_labels = None
depends_on = None


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


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "meal_items", "nutrition_pipeline_version"):
        op.add_column(
            "meal_items",
            sa.Column("nutrition_pipeline_version", sa.String(length=32), nullable=True),
        )
    if not _has_column(bind, "meal_items", "nutrition_source"):
        op.add_column(
            "meal_items",
            sa.Column("nutrition_source", sa.String(length=32), nullable=True),
        )
    if not _has_index(bind, "meal_items", "ix_meal_items_nutrition_pipeline_version"):
        op.create_index(
            "ix_meal_items_nutrition_pipeline_version",
            "meal_items",
            ["nutrition_pipeline_version"],
        )
    if not _has_index(bind, "meal_items", "ix_meal_items_nutrition_source"):
        op.create_index(
            "ix_meal_items_nutrition_source",
            "meal_items",
            ["nutrition_source"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "meal_items", "ix_meal_items_nutrition_source"):
        op.drop_index("ix_meal_items_nutrition_source", table_name="meal_items")
    if _has_index(bind, "meal_items", "ix_meal_items_nutrition_pipeline_version"):
        op.drop_index("ix_meal_items_nutrition_pipeline_version", table_name="meal_items")
    if _has_column(bind, "meal_items", "nutrition_source"):
        op.drop_column("meal_items", "nutrition_source")
    if _has_column(bind, "meal_items", "nutrition_pipeline_version"):
        op.drop_column("meal_items", "nutrition_pipeline_version")
