from app.infrastructure.nutrition.csv_nutrition_provider import aggregate_nutrients


def test_aggregate_nutrients_scales_per_100g_values() -> None:
    ingredients = [{"grams": 150}]
    nutrition_rows = [{"protein": 10, "fiber": 2, "glucose": 1, "water": 70}]
    field_map = {
        "protein": "protein_g",
        "fiber": "fiber_g",
        "glucose": "glucose_g",
        "water": "water_g",
    }

    result = aggregate_nutrients(ingredients, nutrition_rows, field_map)

    assert result["protein_g"] == 15.0
    assert result["fiber_g"] == 3.0
    assert result["glucose_g"] == 1.5
    assert result["water_g"] == 105.0
