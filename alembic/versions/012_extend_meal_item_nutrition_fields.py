"""Extend meal_item_nutrition with detailed nutrients from nutrition.csv."""

from alembic import op
import sqlalchemy as sa

revision = "012_meal_item_nutrients_ext"
down_revision = "011_fiber_g_float"
branch_labels = None
depends_on = None


NEW_COLUMNS: tuple[str, ...] = (
    "serving_size_g",
    "cholesterol_mg",
    "folic_acid_mcg",
    "vitamin_a_rae_mcg",
    "carotene_alpha_mcg",
    "carotene_beta_mcg",
    "cryptoxanthin_beta_mcg",
    "lutein_zeaxanthin_mcg",
    "lycopene_mcg",
    "tocopherol_alpha_mg",
    "alanine_g",
    "arginine_g",
    "aspartic_acid_g",
    "cystine_g",
    "glutamic_acid_g",
    "glycine_g",
    "histidine_g",
    "hydroxyproline_g",
    "isoleucine_g",
    "leucine_g",
    "lysine_g",
    "methionine_g",
    "phenylalanine_g",
    "proline_g",
    "serine_g",
    "threonine_g",
    "tryptophan_g",
    "tyrosine_g",
    "valine_g",
    "fructose_g",
    "galactose_g",
    "glucose_g",
    "lactose_g",
    "maltose_g",
    "sucrose_g",
    "total_fat_g",
    "saturated_fatty_acids_g",
    "monounsaturated_fatty_acids_g",
    "polyunsaturated_fatty_acids_g",
    "fatty_acids_total_trans_g",
    "alcohol_g",
    "ash_g",
    "caffeine_mg",
    "theobromine_mg",
    "water_g",
)


def upgrade() -> None:
    for col in NEW_COLUMNS:
        op.add_column("meal_item_nutrition", sa.Column(col, sa.Float(), nullable=True))


def downgrade() -> None:
    for col in reversed(NEW_COLUMNS):
        op.drop_column("meal_item_nutrition", col)
