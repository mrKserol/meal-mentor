from app.infrastructure.usda.nutrient_mapper import normalize_usda_food_nutrients


def test_maps_full_usda_nutrients_and_ignores_energy_kj():
    food = {
        "foodNutrients": [
            {"amount": 100, "nutrient": {"id": 1008, "name": "Energy", "unitName": "KCAL"}},
            {"amount": 418, "nutrient": {"id": 1008, "name": "Energy", "unitName": "kJ"}},
            {"amount": 12.5, "nutrient": {"id": 1003, "name": "Protein", "unitName": "G"}},
            {"amount": 7.1, "nutrient": {"id": 1004, "name": "Total lipid (fat)", "unitName": "G"}},
            {"amount": 22.2, "nutrient": {"id": 1005, "name": "Carbohydrate, by difference", "unitName": "G"}},
            {"amount": 300, "nutrient": {"id": 1093, "name": "Sodium, Na", "unitName": "MG"}},
            {"amount": 1.23, "nutrient": {"id": 999999, "name": "Unknown", "unitName": "G"}},
        ]
    }

    out = normalize_usda_food_nutrients(food)

    assert out["calories"] == 100
    assert out["protein_g"] == 12.5
    assert out["fat_g"] == 7.1
    assert out["total_fat_g"] == 7.1
    assert out["carbs_g"] == 22.2
    assert out["sodium_mg"] == 300
    assert "unknown" not in out


def test_maps_abridged_usda_nutrients_by_name_and_value():
    food = {
        "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "KCAL", "value": 89},
            {"nutrientName": "Protein", "unitName": "G", "value": 1.1},
            {"nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0.3},
            {"nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 23},
            {"nutrientName": "Fiber, total dietary", "unitName": "G", "value": 2.6},
            {"nutrientName": "Sodium, Na", "unitName": "MG", "value": 1},
            {"nutrientName": "Not a nutrient", "unitName": "G", "value": 99},
        ]
    }

    out = normalize_usda_food_nutrients(food)

    assert out["calories"] == 89
    assert out["protein_g"] == 1.1
    assert out["fat_g"] == 0.3
    assert out["carbs_g"] == 23
    assert out["fiber_g"] == 2.6
    assert out["sodium_mg"] == 1
    assert "not a nutrient" not in out
