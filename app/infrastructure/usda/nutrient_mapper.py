from __future__ import annotations

from typing import Any


USDA_NUTRIENT_ID_MAP = {
    1008: "calories",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carbs_g",
    1079: "fiber_g",
    2000: "sugar_g",
    1093: "sodium_mg",
    1258: "saturated_fat_g",
    1253: "cholesterol_mg",
    1087: "calcium_mg",
    1089: "iron_mg",
    1090: "magnesium_mg",
    1091: "phosphorus_mg",
    1092: "potassium_mg",
    1095: "zinc_mg",
    1098: "copper_mg",
    1101: "manganese_mg",
    1103: "selenium_mcg",
    1162: "vitamin_c_mg",
    1175: "vitamin_b6_mg",
    1178: "vitamin_b12_mcg",
    1177: "folate_mcg",
    1186: "folic_acid_mcg",
    1167: "niacin_mg",
    1166: "riboflavin_mg",
    1165: "thiamin_mg",
    1180: "choline_mg",
    1185: "vitamin_k_mcg",
    1109: "vitamin_e_mg",
}

USDA_NUTRIENT_NAME_MAP = {
    "energy": "calories",
    "protein": "protein_g",
    "total lipid (fat)": "fat_g",
    "carbohydrate, by difference": "carbs_g",
    "fiber, total dietary": "fiber_g",
    "sugars, total including nlea": "sugar_g",
    "sugars, total": "sugar_g",
    "sodium, na": "sodium_mg",
    "fatty acids, total saturated": "saturated_fat_g",
    "cholesterol": "cholesterol_mg",
    "calcium, ca": "calcium_mg",
    "iron, fe": "iron_mg",
    "magnesium, mg": "magnesium_mg",
    "phosphorus, p": "phosphorus_mg",
    "potassium, k": "potassium_mg",
    "zinc, zn": "zinc_mg",
    "copper, cu": "copper_mg",
    "manganese, mn": "manganese_mg",
    "selenium, se": "selenium_mcg",
    "vitamin c, total ascorbic acid": "vitamin_c_mg",
    "vitamin b-6": "vitamin_b6_mg",
    "vitamin b-12": "vitamin_b12_mcg",
    "folate, total": "folate_mcg",
    "folic acid": "folic_acid_mcg",
    "niacin": "niacin_mg",
    "riboflavin": "riboflavin_mg",
    "thiamin": "thiamin_mg",
    "choline, total": "choline_mg",
    "vitamin k (phylloquinone)": "vitamin_k_mcg",
    "vitamin e (alpha-tocopherol)": "vitamin_e_mg",
}


def _get_nutrient_name(row: dict) -> str | None:
    nutrient = row.get("nutrient")
    if isinstance(nutrient, dict):
        name = nutrient.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    name = row.get("nutrientName")
    return name.strip() if isinstance(name, str) and name.strip() else None


def _get_nutrient_unit(row: dict) -> str | None:
    nutrient = row.get("nutrient")
    if isinstance(nutrient, dict):
        unit = nutrient.get("unitName")
        if isinstance(unit, str) and unit.strip():
            return unit.strip()
    unit = row.get("unitName")
    return unit.strip() if isinstance(unit, str) and unit.strip() else None


def _get_nutrient_amount(row: dict) -> float | None:
    value = row.get("amount", row.get("value"))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_nutrient_id(row: dict) -> int | None:
    nutrient = row.get("nutrient")
    raw_id: Any = None
    if isinstance(nutrient, dict):
        raw_id = nutrient.get("id")
    if raw_id is None:
        raw_id = row.get("nutrientId")
    try:
        return int(raw_id)
    except (TypeError, ValueError):
        return None


def _normalize_name(name: str | None) -> str:
    return " ".join((name or "").strip().lower().split())


def normalize_usda_food_nutrients(food: dict) -> dict[str, float]:
    """
    Return internal per-100g nutrient dict.
    """
    rows = food.get("foodNutrients") or []
    if not isinstance(rows, list):
        return {}

    out: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        amount = _get_nutrient_amount(row)
        if amount is None:
            continue

        nutrient_id = _get_nutrient_id(row)
        nutrient_name = _get_nutrient_name(row)
        nutrient_unit = (_get_nutrient_unit(row) or "").strip().lower()
        internal_key = USDA_NUTRIENT_ID_MAP.get(nutrient_id) if nutrient_id is not None else None
        if internal_key is None:
            internal_key = USDA_NUTRIENT_NAME_MAP.get(_normalize_name(nutrient_name))
        if internal_key is None:
            continue

        if internal_key == "calories" and nutrient_unit != "kcal":
            continue
        if internal_key not in out:
            out[internal_key] = amount

    if "fat_g" in out and "total_fat_g" not in out:
        out["total_fat_g"] = out["fat_g"]
    if "saturated_fat_g" in out and "saturated_fatty_acids_g" not in out:
        out["saturated_fatty_acids_g"] = out["saturated_fat_g"]
    return out
