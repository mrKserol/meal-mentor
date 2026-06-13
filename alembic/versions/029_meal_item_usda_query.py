"""add usda_search_query to meal_items"""

from alembic import op
import sqlalchemy as sa

revision = "029_meal_item_usda_query"
down_revision = "028_meal_item_pipeline"
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
    if not _has_column(bind, "meal_items", "usda_search_query"):
        op.add_column(
            "meal_items",
            sa.Column("usda_search_query", sa.String(length=512), nullable=True),
        )
    if not _has_index(bind, "meal_items", "ix_meal_items_usda_search_query"):
        op.create_index(
            "ix_meal_items_usda_search_query",
            "meal_items",
            ["usda_search_query"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "meal_items", "ix_meal_items_usda_search_query"):
        op.drop_index("ix_meal_items_usda_search_query", table_name="meal_items")
    if _has_column(bind, "meal_items", "usda_search_query"):
        op.drop_column("meal_items", "usda_search_query")
