"""Add target_fiber_g to nutrition_targets."""

from alembic import op
import sqlalchemy as sa

revision = "013_target_fiber_g"
down_revision = "012_meal_item_nutrients_ext"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "nutrition_targets", "target_fiber_g"):
        op.add_column("nutrition_targets", sa.Column("target_fiber_g", sa.Float(), nullable=True))
    op.execute(
        """
        UPDATE nutrition_targets
        SET target_fiber_g = ROUND((target_calories::numeric / 1000.0) * 14.0, 1)
        WHERE target_fiber_g IS NULL
        """
    )
    op.alter_column("nutrition_targets", "target_fiber_g", nullable=False)


def downgrade() -> None:
    op.drop_column("nutrition_targets", "target_fiber_g")
