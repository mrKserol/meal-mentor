"""Rename vitamin A/D and trans-fat columns to source units."""

from alembic import op
import sqlalchemy as sa

revision = "014_nutrient_units_iu"
down_revision = "013_target_fiber_g"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _rename_or_drop_duplicate(table: str, old_name: str, new_name: str) -> None:
    bind = op.get_bind()
    old_exists = _has_column(bind, table, old_name)
    new_exists = _has_column(bind, table, new_name)
    if old_exists and not new_exists:
        with op.batch_alter_table(table) as batch_op:
            batch_op.alter_column(old_name, new_column_name=new_name)
    elif old_exists and new_exists:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column(old_name)


def upgrade() -> None:
    _rename_or_drop_duplicate("meal_item_nutrition", "vitamin_a_mcg", "vitamin_a_iu")
    _rename_or_drop_duplicate("meal_item_nutrition", "vitamin_d_mcg", "vitamin_d_iu")
    _rename_or_drop_duplicate(
        "meal_item_nutrition",
        "fatty_acids_total_trans_g",
        "fatty_acids_total_trans_mg",
    )


def downgrade() -> None:
    with op.batch_alter_table("meal_item_nutrition") as batch_op:
        batch_op.alter_column("vitamin_a_iu", new_column_name="vitamin_a_mcg")
        batch_op.alter_column("vitamin_d_iu", new_column_name="vitamin_d_mcg")
        batch_op.alter_column("fatty_acids_total_trans_mg", new_column_name="fatty_acids_total_trans_g")
