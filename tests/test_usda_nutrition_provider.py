from app.infrastructure.nutrition.usda_nutrition_provider import NutritionService2
from app.infrastructure.usda.client import UsdaApiError
from app.infrastructure.usda.food_matcher import UsdaFoodMatcher


class FakeUsdaClient:
    api_key = "test"

    def search_foods(self, query, *, data_types=None, page_size=10):
        return {
            "foods": [
                {
                    "fdcId": 173944,
                    "description": "Bananas, raw",
                    "dataType": "SR Legacy",
                    "foodNutrients": [],
                }
            ]
        }

    def get_food(self, fdc_id):
        return {
            "fdcId": fdc_id,
            "description": "Bananas, raw",
            "dataType": "SR Legacy",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 89},
                {"nutrientId": 1003, "nutrientName": "Protein", "unitName": "G", "value": 1.1},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0.3},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 23},
                {"nutrientId": 1079, "nutrientName": "Fiber, total dietary", "unitName": "G", "value": 2.6},
            ],
        }


class ErrorUsdaClient:
    api_key = "test"

    def search_foods(self, query, *, data_types=None, page_size=10):
        raise UsdaApiError("boom")

    def get_food(self, fdc_id):
        raise UsdaApiError("boom")


class EmptyNutritionService:
    is_available = False

    def search(self, *args, **kwargs):
        return [{"banana": {}}]


def _service(client):
    return NutritionService2(
        matcher=UsdaFoodMatcher(client=client),
        fallback_v1=EmptyNutritionService(),
    )


def test_search_returns_csv_compatible_shape():
    service = _service(FakeUsdaClient())

    out = service.search({"banana": {"grams": 100, "state": "raw"}})

    row = out[0]["banana"]
    assert row["calories"] == 89
    assert row["protein_g"] == 1.1
    assert row["fat_g"] == 0.3
    assert row["carbs_g"] == 23
    assert row["fiber_g"] == 2.6
    assert row["match"] == "USDA: Bananas, raw"
    assert row["weight"] == 100
    assert row["state"] == "raw"
    assert row["fdc_id"] == "173944"
    assert row["data_type"] == "SR Legacy"


def test_aggregate_nutrition_returns_legacy_macro_keys():
    service = _service(FakeUsdaClient())

    out = service.aggregate_nutrition({"banana": {"grams": 200, "state": "raw"}})

    assert out == {
        "calories": 178,
        "proteins": 2,
        "fats": 1,
        "carbohydrates": 46,
    }


def test_aggregate_nutrition_full_returns_internal_keys():
    service = _service(FakeUsdaClient())

    out = service.aggregate_nutrition_full({"banana": {"grams": 100, "state": "raw"}})

    assert out is not None
    assert out["calories"] == 89
    assert out["protein_g"] == 1.1
    assert out["fat_g"] == 0.3
    assert out["carbs_g"] == 23


def test_usda_client_error_does_not_crash_provider():
    service = _service(ErrorUsdaClient())

    assert service.search({"banana": {"grams": 100, "state": "raw"}}) == [{"banana": {}}]
    assert service.aggregate_nutrition({"banana": {"grams": 100, "state": "raw"}}) is None
    assert service.aggregate_nutrition_full({"banana": {"grams": 100, "state": "raw"}}) is None
