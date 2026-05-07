"""Rename vitamin A/D and trans-fat columns to source units."""

from alembic import op

revision = "014_nutrient_units_iu"
down_revision = "013_target_fiber_g"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("meal_item_nutrition") as batch_op:
        batch_op.alter_column("vitamin_a_mcg", new_column_name="vitamin_a_iu")
        batch_op.alter_column("vitamin_d_mcg", new_column_name="vitamin_d_iu")
        batch_op.alter_column("fatty_acids_total_trans_g", new_column_name="fatty_acids_total_trans_mg")


def downgrade() -> None:
    with op.batch_alter_table("meal_item_nutrition") as batch_op:
        batch_op.alter_column("vitamin_a_iu", new_column_name="vitamin_a_mcg")
        batch_op.alter_column("vitamin_d_iu", new_column_name="vitamin_d_mcg")
        batch_op.alter_column("fatty_acids_total_trans_mg", new_column_name="fatty_acids_total_trans_g")
