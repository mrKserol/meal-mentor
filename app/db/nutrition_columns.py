"""Column names on MealItemNutrition used when persisting CSV-derived rows (excluding id, meal_item_id, created_at)."""

from sqlalchemy import Column, Float, Integer

MEAL_ITEM_NUTRITION_KEYS: tuple[str, ...] = (
    "calories",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    "sugar_g",
    "serving_size_g",
    "cholesterol_mg",
    "saturated_fat_g",
    "folic_acid_mcg",
    "sodium_mg",
    "calcium_mg",
    "magnesium_mg",
    "potassium_mg",
    "phosphorus_mg",
    "iron_mg",
    "zinc_mg",
    "selenium_mcg",
    "copper_mg",
    "manganese_mg",
    "vitamin_a_iu",
    "vitamin_a_rae_mcg",
    "carotene_alpha_mcg",
    "carotene_beta_mcg",
    "cryptoxanthin_beta_mcg",
    "lutein_zeaxanthin_mcg",
    "lycopene_mcg",
    "vitamin_c_mg",
    "vitamin_d_iu",
    "vitamin_e_mg",
    "tocopherol_alpha_mg",
    "vitamin_k_mcg",
    "vitamin_b6_mg",
    "vitamin_b12_mcg",
    "folate_mcg",
    "thiamin_mg",
    "riboflavin_mg",
    "niacin_mg",
    "pantothenic_acid_mg",
    "choline_mg",
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
    "fatty_acids_total_trans_mg",
    "alcohol_g",
    "ash_g",
    "caffeine_mg",
    "theobromine_mg",
    "water_g",
)

INTEGER_NUTRITION_KEYS: frozenset[str] = frozenset(
    {"calories", "protein_g", "fat_g", "carbs_g", "sugar_g", "sodium_mg"},
)


def nutrition_column(key: str) -> Column:
    """SQLAlchemy column for a meal-item nutrient field (Additive / AdditiveIntake)."""
    if key in INTEGER_NUTRITION_KEYS:
        return Column(Integer, nullable=True)
    return Column(Float, nullable=True)


def apply_nutrition_columns_to_model(model_cls: type) -> None:
    """Attach MEAL_ITEM_NUTRITION_KEYS columns to a declarative model class."""
    for key in MEAL_ITEM_NUTRITION_KEYS:
        setattr(model_cls, key, nutrition_column(key))
